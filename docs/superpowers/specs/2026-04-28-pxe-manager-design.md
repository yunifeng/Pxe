# PXE Manager 设计文档

> 日期: 2026-04-28
> 状态: 已批准

## 项目概述

PXE Manager 是一个基于 Web 的 PXE 网络启动分布式（master/agent）管理系统，用于自动化部署和管理服务器操作系统安装。目标在网页上完成 PXE 操作配置，部署环境定位为 Ubuntu 22.04 live-server 系统。

## 技术栈

| 层面 | 技术 | 说明 |
|------|------|------|
| 后端 | Python FastAPI | RESTful API + WebSocket 实时推送 |
| 前端 | Vue 3 + Element Plus | 管理后台 UI |
| 数据库 | SQLite | Master 和 Agent 统一使用，Master 通过 SSH 读取 Agent 数据 |
| 部署 | Ubuntu 22.04 | 一键部署脚本 |
| BMC | python-ipmi + Redfish SDK | BMC/IPMI 集成 |
| 认证 | JWT + bcrypt | 本地用户 + 角色权限 |

## 核心功能

1. **仪表盘** — 节点、主机、BMC 等统计，系统状态，常用操作快捷跳转
2. **PXE 服务** — dnsmasq 服务控制、iPXE 引导菜单、配置查看/编辑、DHCP 配置、ISO 镜像、安装任务、安装报告、MAC 过滤、日志查看
3. **节点管理** — 集群节点信息、状态监控、节点控制、远程 SSH
4. **BMC 管理** — BMC 列表、BMC 统计、单个/批量添加、状态显示、BMC 电源操作
5. **配置模板** — user-data/Kickstart/Preseed 模板管理
6. **文件管理** — 文件分类、agent 同步选项、脚本/软件仓库可供 PXE 使用
7. **主机管理** — 主机列表、远程 SSH 连接、集成 Ansible 可操作远程主机、硬件清单

## 部署模式

- **Agent 节点为主** — agent 节点可完全离线运行且不影响功能，镜像和文件本地存放
- **Master 节点** — 全方位统计展示数据、远程控制 agent 节点、文件同步、远程连接

## 项目目录结构

```
pxe/
├── backend/                 # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # 应用入口，根据模式加载不同路由
│   │   ├── config.py        # 配置管理（部署模式、数据库路径等）
│   │   ├── database.py      # SQLite 数据库连接
│   │   ├── models.py        # SQLAlchemy 数据模型
│   │   ├── auth/            # 认证与权限
│   │   │   ├── jwt_handler.py
│   │   │   ├── roles.py
│   │   │   └── deps.py
│   │   ├── pxe/             # PXE 服务管理
│   │   │   ├── dnsmasq.py   # dnsmasq 配置生成与控制
│   │   │   ├── tftp.py      # TFTP 服务管理
│   │   │   ├── ipxe.py      # iPXE 引导菜单
│   │   │   ├── iso.py       # ISO 镜像管理
│   │   │   └── tasks.py     # 安装任务/报告
│   │   ├── bmc/             # BMC 管理
│   │   │   ├── ipmi_handler.py
│   │   │   ├── redfish_handler.py
│   │   │   └── batch.py     # 批量操作
│   │   ├── node/            # 节点管理
│   │   │   ├── agent.py     # Agent 本地 CLI 工具
│   │   │   ├── ssh.py       # SSH 远程执行
│   │   │   └── monitor.py   # 状态监控
│   │   ├── host/            # 主机管理
│   │   │   ├── ansible.py   # Ansible 集成
│   │   │   └── inventory.py # 硬件清单
│   │   ├── filemgr/         # 文件管理
│   │   │   ├── sync.py      # Agent 同步
│   │   │   └── repo.py      # 脚本/软件仓库
│   │   ├── template/        # 配置模板
│   │   │   └── preseed.py   # user-data/Kickstart/Preseed
│   │   ├── api/             # API 路由
│   │   │   ├── dashboard.py
│   │   │   ├── pxe.py
│   │   │   ├── bmc.py
│   │   │   ├── node.py
│   │   │   ├── host.py
│   │   │   ├── filemgr.py
│   │   │   └── template.py
│   │   └── utils/           # 工具函数
│   │       ├── systemd.py   # Systemd 服务控制
│   │       └── logs.py      # 日志管理
│   ├── requirements.txt
│   └── cli.py               # Agent 本地 CLI 入口（供 master SSH 调用）
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── views/           # 页面组件
│   │   │   ├── Dashboard.vue
│   │   │   ├── PXE/
│   │   │   ├── BMC/
│   │   │   ├── Node/
│   │   │   ├── Host/
│   │   │   ├── FileMgr/
│   │   │   └── Template/
│   │   ├── components/      # 通用组件
│   │   ├── router/          # 路由配置
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── api/             # API 调用层
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
├── scripts/
│   └── deploy-ubuntu22.sh   # 一键部署脚本
└── docs/
    └── superpowers/specs/
```

## 数据模型

### 节点 (Node)
集群中的 agent 节点信息
- id, hostname, IP, 部署模式(master/agent), 状态(online/offline), 最后心跳时间, 创建/更新时间

### BMC (BmcInfo)
服务器 BMC 信息
- id, hostname, BMC IP, 用户名, 密码(加密), 协议(ipmi/redfish), 电源状态, 关联主机 ID, 状态

### 主机 (Host)
被管理的物理服务器
- id, hostname, IP, MAC 地址, 关联节点 ID, BMC ID, 操作系统, 部署状态(pending/installing/running/failed), 安装进度, 错误信息

### PXE 配置 (PxeConfig)
PXE 服务配置
- id, 节点 ID, dnsmasq 配置内容, TFTP 根目录, iPXE 菜单内容, DHCP 配置, MAC 过滤规则, 状态(enabled/disabled)

### ISO 镜像 (IsoImage)
ISO 镜像管理
- id, 名称, 本地路径, 大小, 架构(x86_64/arm64), 关联节点 ID, 状态(available/active)

### 安装任务 (InstallTask)
系统安装任务
- id, 主机 ID, ISO ID, 模板 ID, 节点 ID, 状态(pending/running/completed/failed), 进度百分比, 开始/完成时间, 日志路径

### 安装报告 (InstallReport)
安装结果报告
- id, 任务 ID, 结果(success/failed), 持续时间, 错误详情, 报告内容

### 文件 (FileInfo)
文件管理
- id, 名称, 类型(script/config/repo), 路径, 大小, 分类, 同步状态(synced/pending), 关联节点 ID

### 配置模板 (Template)
Preseed/Kickstart 模板
- id, 名称, 类型(user-data/kickstart/preseed), 内容, 描述, 默认值(JSON), 创建/更新时间

### 用户 (User)
系统用户
- id, 用户名, 密码哈希, 角色(admin/operator/readonly), 创建时间, 最后登录时间

## API 路由

所有 API 在 `/api/v1` 前缀下：

| 方法 | 路由 | 说明 |
|------|------|------|
| GET | `/dashboard` | 仪表盘数据 |
| GET/PUT | `/pxe/config` | PXE 配置 |
| GET | `/pxe/services` | 服务状态 |
| POST | `/pxe/services/{name}/control` | 服务启停 |
| GET/POST | `/bmc` | BMC 列表/批量添加 |
| POST | `/bmc/{id}/power/{action}` | 电源操作 |
| GET/POST | `/node` | 节点列表/控制 |
| GET/POST | `/host` | 主机列表/操作 |
| GET/POST | `/file` | 文件管理 |
| POST | `/file/sync` | 文件同步 |
| GET/POST | `/template` | 模板管理 |
| POST | `/auth/login` | 登录 |
| GET | `/auth/profile` | 用户信息 |
| POST | `/auth/logout` | 登出 |

**认证流程：** 用户登录 → 验证凭据 → 返回 JWT token → 后续请求携带 `Authorization: Bearer <token>` → 路由级权限检查

**错误处理统一格式：** `{"success": false, "error": {"code": "错误码", "message": "错误信息"}}`

## 通信方式

### Master → Agent
Master 通过 SSH 连接到 agent 节点，执行 `pxe-cli` CLI 工具获取数据或执行操作。

**Agent CLI 命令：**
- `status` — 返回节点状态和服务状态
- `pxe-config` — 获取/设置 PXE 配置
- `bmc-list` — 列出本地 BMC 信息
- `bmc-power` — 电源操作
- `install-task` — 创建/查询安装任务
- `file-sync` — 同步文件到本地
- `log` — 查看日志

### 前端 ↔ 后端
使用 **WebSocket** 推送实时数据到前端：
- 安装任务进度更新 → 前端实时显示
- BMC 批量操作结果 → 逐个推送
- 服务状态变化（dnsmasq 停止/TFTP 异常）→ 前端弹出通知
- Agent 节点在线状态 → 实时更新

## 核心业务流程

### 一键部署
1. 运行 `sudo bash scripts/deploy-ubuntu22.sh master` 或 `agent`
2. 脚本检测系统环境（Ubuntu 22.04、网络配置、依赖包）
3. 安装依赖：Python、Node.js、dnsmasq、TFTP、ipxe、paramiko、python-ipmi 等
4. 配置 systemd 服务：`pxe-backend.service`、`pxe-frontend.service`
5. 初始化数据库、创建默认管理员账号
6. 配置防火墙规则（PXE 需要开放 DHCP、TFTP、HTTP 端口）
7. Master 模式额外配置 SSH 密钥（用于连接 agent）

### PXE 启动
1. 客户端通过网络启动，发送 DHCP 请求
2. dnsmasq 分配 IP 并返回 TFTP 服务器地址和引导文件
3. 客户端从 TFTP 下载 iPXE 引导程序
4. iPXE 执行引导菜单，根据 MAC 地址匹配安装任务
5. 加载内核和初始化 RAM 磁盘，挂载 Preseed 配置
6. Ubuntu 22.04 自动安装，完成后报告结果

### 安装任务
1. 用户在 Web 界面选择主机和 ISO 镜像
2. 选择 Preseed 模板并自定义配置（分区、密码等）
3. 系统生成 dnsmasq 配置（MAC 地址到引导文件映射）
4. 生成 iPXE 菜单项（针对该主机的特定安装）
5. 重启主机 → BMC 电源 → 设置网络启动 → 开始安装
6. WebSocket 实时更新任务状态，前端实时显示进度
7. 安装完成后生成报告（成功/失败、耗时、错误信息）

### 文件同步（Master → Agent）
1. 用户在 master 上传或修改文件（脚本、配置、模板）
2. 标记文件为"待同步"状态
3. Master 通过 SSH 连接到目标 agent 节点
4. 使用 `pxe-cli file-sync` 命令同步文件到本地
5. Agent 验证文件完整性并更新状态
6. 同步完成后更新数据库中的同步状态

### BMC 批量操作
1. 用户选择多个 BMC 实例（支持全选/按条件筛选）
2. 选择操作（开机/关机/重启/强制关机）
3. 系统并行执行 BMC 操作（使用线程池）
4. 实时显示各 BMC 的操作状态和结果
5. 生成操作报告（成功/失败列表）

## 安全设计

### 安全措施
- **密码存储** — 使用 bcrypt 哈希，不存储明文密码
- **BMC 凭据加密** — 使用 Fernet 对称加密存储数据库，密钥保存在 `/root/.pxe/secret.key`
- **SSH 密钥管理** — master 通过 SSH 连接 agent，使用无密码密钥对，密钥文件权限 600
- **JWT 签名** — 使用 HS256 算法，密钥从配置文件读取，token 有效期 24 小时
- **输入验证** — 所有 API 输入使用 Pydantic 模型验证，防止 SQL 注入、命令注入
- **CORS** — 仅允许前端域名访问 API
- **速率限制** — 登录接口限制 5 次/分钟，防止暴力破解

### 错误处理
- **统一错误码** — 每个操作定义明确的错误码（如 `BMC_POWER_FAILED`、`SSH_CONNECTION_REFUSED`）
- **日志记录** — 使用 Python logging 模块，按日期轮转，保留 30 天
- **服务健康检查** — 定期检查 dnsmasq、TFTP 等服务状态，异常时记录日志并通知前端
- **任务失败重试** — 安装任务支持手动重试，自动记录失败原因
- **SSH 连接超时** — 设置 30 秒超时，失败后记录详细错误信息
- **数据库锁处理** — SQLite 并发写入时使用重试机制（最多 3 次，间隔 100ms）

### 前端错误提示
- 操作失败显示具体错误信息（非技术用户友好）
- 网络错误提示检查 agent 节点状态
- 表单验证实时提示（如 BMC IP 格式、密码强度）

### 部署安全
- 部署脚本检测 root 权限，非 root 拒绝执行
- 服务直接以 root 运行
- 配置文件和日志文件由 root 管理
- 密钥文件保存在 `/root/.pxe/secret.key`，权限 600

## 测试策略

### 分层测试
1. **单元测试** — 使用 `pytest`，覆盖核心逻辑层
   - 配置生成（dnsmasq、iPXE 引导菜单渲染）
   - 认证逻辑（JWT 签发/验证、角色权限检查）
   - 数据模型（创建、查询、关联关系）
   - BMC 操作封装（Mock IPMI/Redfish 调用）
   - 文件同步逻辑（Mock SSH）

2. **集成测试** — 使用 `pytest` + SQLite 内存数据库
   - API 端点测试（FastAPI TestClient）
   - 数据库操作（插入、查询、更新、删除）
   - 完整业务流程（创建任务 → 更新状态 → 生成报告）

3. **E2E 测试** — 使用 Playwright
   - 登录/登出流程
   - 创建 PXE 配置
   - BMC 批量操作界面
   - 安装任务创建与状态跟踪

**测试目标：** 核心逻辑覆盖率 80%+，API 端点 100% 覆盖

## 部署架构

```
┌─────────────────────────────────┐
│         Master 节点              │
│  ┌──────────┐  ┌─────────────┐  │
│  │ Vue 前端  │  │  FastAPI    │  │
│  │ :5173    │→ │  API :8000  │  │
│  └──────────┘  └──────┬──────┘  │
│                       │ SSH     │
│              ┌────────▼────────┐ │
│              │  SQLite DB      │ │
│              │  /opt/pxe/data/ │ │
│              └─────────────────┘ │
└──────────────┬──────────────────┘
               │ SSH
               ▼
┌─────────────────────────────────┐
│         Agent 节点               │
│  ┌──────────┐  ┌─────────────┐  │
│  │ Vue 前端  │  │  FastAPI    │  │
│  │ :5173    │→ │  API :8000  │  │
│  └──────────┘  └──────┬──────┘  │
│                       │          │
│         ┌─────────────┐         │
│         │  SQLite DB  │         │
│         │ /opt/pxe/   │         │
│         └─────────────┘         │
└─────────────────────────────────┘
```

## 关键设计原则

- **Agent 离线优先** — agent 节点可完全离线运行且不影响功能，镜像和文件本地存放
- **Master 远程控制** — master 节点通过 SSH 管理 agent，agent 无需感知 master 存在
- **单体前后端分离** — 单一 FastAPI 应用 + 单一 Vue 前端，通过模块化保持清晰边界
- **Systemd 配置生成** — FastAPI 后端生成 dnsmasq/TFTP 等配置文件，通过 systemd 控制服务启停
