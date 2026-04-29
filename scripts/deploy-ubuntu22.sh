#!/usr/bin/env bash
set -euo pipefail

# PXE Manager - One-click deployment script for Ubuntu 22.04
# Usage: ./deploy-ubuntu22.sh [master|agent]

INSTALL_DIR="/opt/pxe"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DATA_DIR="${INSTALL_DIR}/data"
IMAGES_DIR="${INSTALL_DIR}/images"
FILES_DIR="${INSTALL_DIR}/files"
LOG_DIR="${INSTALL_DIR}/logs"
TFTP_DIR="${INSTALL_DIR}/tftpboot"
SECRET_DIR="/root/.pxe"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERR]${NC} $*"; }

# ── Task 151: Parameter parsing & preflight checks ──────────────────────────

parse_args() {
    APP_MODE="${1:-agent}"
    if [[ "$APP_MODE" != "master" && "$APP_MODE" != "agent" ]]; then
        error "Invalid mode: $APP_MODE (must be 'master' or 'agent')"
        echo "Usage: $0 [master|agent]"
        exit 1
    fi
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
        exit 1
    fi
}

check_ubuntu22() {
    local version
    version=$(. /etc/os-release && echo "$VERSION_ID")
    if [[ "$version" != "22.04" ]]; then
        warn "Expected Ubuntu 22.04, detected $version — continuing anyway"
    fi
}

# ── Task 152: Install system dependencies ───────────────────────────────────

install_dependencies() {
    info "Installing system packages..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq

    apt-get install -y -qq \
        dnsmasq tftp-hpa ipxe openssh-server \
        python3 python3-pip python3-venv \
        curl ufw rsync > /dev/null 2>&1

    # Node.js 20.x
    if ! command -v node &> /dev/null; then
        info "Installing Node.js 20.x..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
        apt-get install -y -qq nodejs > /dev/null 2>&1
    fi

    # Backend Python dependencies
    info "Installing Python dependencies..."
    local venv="${INSTALL_DIR}/.venv"
    if [[ ! -d "$venv" ]]; then
        python3 -m venv "$venv"
    fi
    "${venv}/bin/pip" install --upgrade pip > /dev/null 2>&1
    if [[ -f "${PROJECT_DIR}/backend/requirements.txt" ]]; then
        "${venv}/bin/pip" install -r "${PROJECT_DIR}/backend/requirements.txt" > /dev/null 2>&1
    fi

    # Frontend build (after rsync to install dir)
    # NOTE: this is called after create_directories copies source files

    info "Dependencies installed"
}

# ── Task 153: Create directory structure ─────────────────────────────────────

create_directories() {
    info "Creating directory structure..."
    mkdir -p \
        "$DATA_DIR" \
        "$IMAGES_DIR" \
        "$FILES_DIR" \
        "$LOG_DIR" \
        "$TFTP_DIR" \
        "${TFTP_DIR}/ipxe" \
        "${TFTP_DIR}/pxelinux.cfg" \
        "$SECRET_DIR"

    # Copy project files to install directory
    if [[ "$PROJECT_DIR" != "$INSTALL_DIR" ]]; then
        info "Copying project files to ${INSTALL_DIR}..."
        # Avoid copying unnecessary directories
        rsync -a --exclude='node_modules' --exclude='dist' \
            --exclude='.git' --exclude='.venv' \
            "${PROJECT_DIR}/" "${INSTALL_DIR}/"
    fi

    # Build frontend in install directory
    if [[ -f "${INSTALL_DIR}/frontend/package.json" ]]; then
        info "Building frontend..."
        cd "${INSTALL_DIR}/frontend"
        npm install --silent > /dev/null 2>&1
        npm run build > /dev/null 2>&1
        cd - > /dev/null
    fi

    info "Directories created"
}

# ── Task 154: Generate configuration ─────────────────────────────────────────

generate_config() {
    info "Generating configuration..."

    # Fernet key
    if [[ ! -f "${SECRET_DIR}/secret.key" ]]; then
        python3 -c "from cryptography.fernet import Fernet; open('${SECRET_DIR}/secret.key','w').write(Fernet.generate_key().decode())"
        chmod 600 "${SECRET_DIR}/secret.key"
    fi

    # JWT secret
    local jwt_secret
    jwt_secret=$(python3 -c "import secrets; print(secrets.token_hex(32))")

    # .env file
    cat > "${INSTALL_DIR}/.env" <<EOF
APP_MODE=${APP_MODE}
DB_PATH=${DATA_DIR}/pxe.db
JWT_SECRET=${jwt_secret}
JWT_EXPIRE_MINUTES=1440
FERNET_KEY_PATH=${SECRET_DIR}/secret.key
SSH_KEY_PATH=/root/.ssh/pxe_id_ed25519
LOG_DIR=${LOG_DIR}
TFTP_ROOT=${TFTP_DIR}
IMAGES_DIR=${IMAGES_DIR}
FILES_DIR=${FILES_DIR}
EOF

    info "Configuration generated"
}

# ── Task 155: Systemd service files ──────────────────────────────────────────

install_systemd_services() {
    info "Installing systemd services..."

    local venv="${INSTALL_DIR}/.venv"
    local frontend_dist="${INSTALL_DIR}/frontend/dist"

    # Backend service
    cat > /etc/systemd/system/pxe-backend.service <<EOF
[Unit]
Description=PXE Manager Backend API
After=network.target

[Service]
Type=simple
WorkingDirectory=${INSTALL_DIR}/backend
EnvironmentFile=${INSTALL_DIR}/.env
ExecStart=${venv}/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5
StandardOutput=append:${LOG_DIR}/backend.log
StandardError=append:${LOG_DIR}/backend.log

[Install]
WantedBy=multi-user.target
EOF

    # Frontend service (using Python http.server as a simple static server)
    if [[ -d "$frontend_dist" ]]; then
        cat > /etc/systemd/system/pxe-frontend.service <<EOF
[Unit]
Description=PXE Manager Frontend
After=network.target

[Service]
Type=simple
WorkingDirectory=${frontend_dist}
ExecStart=/usr/bin/python3 -m http.server 5173 --bind 0.0.0.0
Restart=on-failure
RestartSec=5
StandardOutput=append:${LOG_DIR}/frontend.log
StandardError=append:${LOG_DIR}/frontend.log

[Install]
WantedBy=multi-user.target
EOF
    fi

    systemctl daemon-reload
    systemctl enable pxe-backend
    if systemctl list-unit-files | grep -q pxe-frontend.service; then
        systemctl enable pxe-frontend
    fi

    info "Systemd services installed"
}

# ── Task 156: PXE service initialization ─────────────────────────────────────

init_pxe_service() {
    info "Initializing PXE boot files..."

    # Copy iPXE binaries
    if command -v ipxe_bin &> /dev/null || [[ -f /usr/lib/ipxe/ipxe.lkrn ]]; then
        cp -n /usr/lib/ipxe/ipxe.lkrn "${TFTP_DIR}/ipxe/" 2>/dev/null || true
        cp -n /usr/lib/ipxe/undionly.kpxe "${TFTP_DIR}/ipxe/" 2>/dev/null || true
    fi

    # Default iPXE boot menu
    cat > "${TFTP_DIR}/ipxe/boot.ipxe" <<'EOF'
#!ipxe

:set menu_timeout 60000

:menu
    item ---             --- Select Boot Option ---
    item :ubuntu22       Ubuntu Server 22.04
    item :centos9        CentOS Stream 9
    item :reboot         Reboot
    item :shell          iPXE Shell
    choose --default ubuntu22 --timeout #{menu_timeout} target && goto #{target}

:ubuntu22
    kernel http://#{server}/images/vmlinuz-ubuntu22 ipnet0/mac=#{net0/mac} initrd=initrd.img auto=true priority=critical
    initrd http://#{server}/images/initrd.img-ubuntu22
    boot

:centos9
    kernel http://#{server}/images/vmlinuz-centos9 ipnet0/mac=#{net0/mac} initrd=initrd.img
    initrd http://#{server}/images/initrd.img-centos9
    boot

:reboot
    reboot

:shell
    shell
EOF

    # Default PXELINUX config (chainload to iPXE)
    cat > "${TFTP_DIR}/pxelinux.cfg/default" <<'EOF'
DEFAULT ipxe
PROMPT 0
TIMEOUT 0
LABEL ipxe
    KERNEL ipxe/undionly.kpxe
EOF

    info "PXE boot files initialized"
}

# ── Task 157: Database initialization ────────────────────────────────────────

init_database() {
    info "Initializing database..."

    local venv="${INSTALL_DIR}/.venv"
    export APP_MODE
    export DB_PATH="${DATA_DIR}/pxe.db"
    export FERNET_KEY_PATH="${SECRET_DIR}/secret.key"
    export LOG_DIR
    export TFTP_ROOT="${TFTP_DIR}"
    export IMAGES_DIR
    export FILES_DIR
    # Source .env for uvicorn environment
    set -a && source "${INSTALL_DIR}/.env" && set +a

    cd "${INSTALL_DIR}"
    cd "${INSTALL_DIR}/backend"
    "${venv}/bin/python3" -c "
import sys
sys.path.insert(0, '.')
from app.database import Base, SessionLocal, engine
from app.models import User, Node
from app.config import settings

# Create tables
Base.metadata.create_all(bind=engine)

# Create default admin user if not exists
db = SessionLocal()
try:
    existing = db.query(User).filter(User.username == 'admin').first()
    if not existing:
        admin = User(
            username='admin',
            password='admin123',
            role='admin',
        )
        db.add(admin)
        db.commit()
        print('Created default admin user (password: admin123)')
    else:
        print('Admin user already exists')

    # In agent mode, create local node record
    if settings.app_mode == 'agent':
        import socket
        hostname = socket.gethostname()
        import fcntl, struct, socket as s
        try:
            sock = s.socket(s.AF_INET, s.SOCK_DGRAM)
            ip = socket.inet_ntoa(fcntl.ioctl(sock.fileno(), 0x8915, struct.pack('256s', b'eth0'[:15]))[20:24])
        except Exception:
            ip = '127.0.0.1'
        node = db.query(Node).filter(Node.hostname == hostname).first()
        if not node:
            node = Node(hostname=hostname, ip=ip, mode='agent', status='online')
            db.add(node)
            db.commit()
            print(f'Created local agent node: {hostname} ({ip})')
        else:
            print('Local agent node already exists')
finally:
    db.close()
print('Database initialized')
"

    info "Database initialized"
}

# ── Task 158: Firewall configuration ─────────────────────────────────────────

config_firewall() {
    info "Configuring firewall..."

    # Allow essential services
    ufw allow ssh > /dev/null 2>&1 || true
    ufw allow 67/udp > /dev/null 2>&1 || true   # DHCP
    ufw allow 69/udp > /dev/null 2>&1 || true   # TFTP
    ufw allow 80/tcp > /dev/null 2>&1 || true   # HTTP (iPXE boot files)
    ufw allow 8000/tcp > /dev/null 2>&1 || true # API
    ufw allow 5173/tcp > /dev/null 2>&1 || true # Frontend

    if [[ "$APP_MODE" == "agent" ]]; then
        # Agent-specific ports
        ufw allow 69/udp > /dev/null 2>&1 || true   # TFTP server
        ufw allow 4011:4020/udp > /dev/null 2>&1 || true # DHCP range
    fi

    # Enable ufw non-interactively if not already active
    if ! ufw status | grep -q "active"; then
        echo "y" | ufw enable > /dev/null 2>&1 || true
    fi

    info "Firewall configured"
}

# ── Task 159: Master mode extra configuration ────────────────────────────────

config_master() {
    if [[ "$APP_MODE" != "master" ]]; then
        return
    fi

    info "Configuring Master node..."

    # Generate SSH key for Master -> Agent connectivity
    if [[ ! -f /root/.ssh/pxe_id_ed25519 ]]; then
        ssh-keygen -t ed25519 -f /root/.ssh/pxe_id_ed25519 -N "" -q
        chmod 600 /root/.ssh/pxe_id_ed25519
        chmod 644 /root/.ssh/pxe_id_ed25519.pub
        info "SSH key generated: /root/.ssh/pxe_id_ed25519"
    fi

    # SSH config for agent connections
    if [[ ! -f /root/.ssh/config ]]; then
        touch /root/.ssh/config
        chmod 600 /root/.ssh/config
    fi

    # Add PXE agent IdentityFile if not already present
    if ! grep -q "pxe_id_ed25519" /root/.ssh/config 2>/dev/null; then
        cat >> /root/.ssh/config <<'EOF'

# PXE Agent connections
Host pxe-agent-*
    IdentityFile ~/.ssh/pxe_id_ed25519
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
EOF
    fi

    info "Master configuration complete"
}

# ── Task 160: Deployment verification ────────────────────────────────────────

verify_deployment() {
    info "Verifying deployment..."

    local ok=0
    local fail=0

    # Start backend service
    systemctl start pxe-backend
    sleep 2

    # Check backend service
    if systemctl is-active --quiet pxe-backend; then
        info "Backend service: active"
        ((ok++))
    else
        error "Backend service: inactive"
        ((fail++))
    fi

    # Check API health endpoint
    local health
    health=$(curl -sf http://localhost:8000/api/v1/health 2>/dev/null || echo "")
    if [[ -n "$health" ]]; then
        info "API health check: OK"
        ((ok++))
    else
        warn "API health check: no response (service may need more time)"
        ((fail++))
    fi

    # Check frontend
    if systemctl list-unit-files | grep -q pxe-frontend.service; then
        systemctl start pxe-frontend
        if systemctl is-active --quiet pxe-frontend; then
            info "Frontend service: active"
        else
            warn "Frontend service: inactive"
        fi
        ((ok++))
    fi

    # Check directory structure
    for dir in "$DATA_DIR" "$IMAGES_DIR" "$FILES_DIR" "$LOG_DIR" "$TFTP_DIR"; do
        if [[ -d "$dir" ]]; then
            ((ok++))
        else
            error "Missing directory: $dir"
            ((fail++))
        fi
    done

    # Check TFTP files
    if [[ -f "${TFTP_DIR}/ipxe/boot.ipxe" && -f "${TFTP_DIR}/pxelinux.cfg/default" ]]; then
        info "PXE boot files: present"
        ((ok++))
    else
        error "PXE boot files: missing"
        ((fail++))
    fi

    echo ""
    info "═══════════════════════════════════════════════════════"
    info "  Deployment Summary"
    info "═══════════════════════════════════════════════════════"
    info "  Mode:           ${APP_MODE}"
    info "  Install dir:    ${INSTALL_DIR}"
    info "  Checks passed:  ${ok}"
    if [[ $fail -gt 0 ]]; then
        warn "  Checks failed:  ${fail}"
    fi
    info ""
    info "  API endpoint:   http://<server-ip>:8000"
    info "  Frontend:       http://<server-ip>:5173"
    info "  Default login:  admin / admin123"
    info "═══════════════════════════════════════════════════════"

    if [[ $fail -gt 0 ]]; then
        warn "Some checks failed — check ${LOG_DIR}/backend.log for details"
        return 1
    fi
    info "All checks passed!"
}

# ── Main ──────────────────────────────────────────────────────────────────────

main() {
    parse_args "$@"
    check_root
    check_ubuntu22

    echo ""
    info "Starting PXE Manager deployment (mode: ${APP_MODE})"
    echo ""

    install_dependencies
    create_directories
    generate_config
    install_systemd_services
    init_pxe_service
    init_database
    config_firewall
    config_master
    verify_deployment

    echo ""
    info "Deployment complete!"
}

main "$@"
