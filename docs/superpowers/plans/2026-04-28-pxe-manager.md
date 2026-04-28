# PXE Manager 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **基于设计文档:** `docs/superpowers/specs/2026-04-28-pxe-manager-design.md`

**Goal:** 构建完整的 PXE 网络启动分布式管理系统，支持 Web 界面配置 PXE、BMC 电源管理、服务器操作系统自动化部署

**Architecture:** 单体前后端分离架构 — FastAPI 后端 + Vue 3 前端，通过配置区分 master/agent 模式。Agent 节点完全离线运行，Master 通过 SSH + CLI 工具远程控制 Agent。SQLite 全局存储，WebSocket 实时推送。

**Tech Stack:** Python FastAPI, Vue 3, Element Plus, SQLite, SQLAlchemy, JWT, paramiko, python-ipmi, Redfish SDK, systemd

## 文件结构总览

本计划会创建或修改以下文件，按阶段分组：

### 阶段 1 — 项目基础
| 文件 | 职责 |
|------|------|
| `backend/requirements.txt` | Python 依赖 |
| `backend/app/__init__.py` | 包初始化 |
| `backend/app/main.py` | FastAPI 应用入口 |
| `backend/app/config.py` | 配置管理 (部署模式、数据库路径等) |
| `backend/app/database.py` | SQLite 数据库引擎与会话 |
| `backend/app/models.py` | SQLAlchemy 数据模型 |
| `backend/tests/` | 后端测试目录 |

### 阶段 2 — 认证系统
| 文件 | 职责 |
|------|------|
| `backend/app/auth/jwt_handler.py` | JWT 签发/验证 |
| `backend/app/auth/roles.py` | 角色定义与权限检查 |
| `backend/app/auth/deps.py` | FastAPI 依赖注入 (当前用户、角色校验) |
| `backend/app/api/auth.py` | 登录/登出 API |

### 阶段 3 — 工具层
| 文件 | 职责 |
|------|------|
| `backend/app/utils/systemd.py` | Systemd 服务控制 (start/stop/restart/status) |
| `backend/app/utils/logs.py` | 日志配置与轮转 |

### 阶段 4 — PXE 服务管理
| 文件 | 职责 |
|------|------|
| `backend/app/pxe/dnsmasq.py` | dnsmasq 配置生成与控制 |
| `backend/app/pxe/tftp.py` | TFTP 服务管理 |
| `backend/app/pxe/ipxe.py` | iPXE 引导菜单生成 |
| `backend/app/pxe/iso.py` | ISO 镜像管理 |
| `backend/app/pxe/tasks.py` | 安装任务/报告 |
| `backend/app/api/pxe.py` | PXE API 路由 |

### 阶段 5 — BMC 管理
| 文件 | 职责 |
|------|------|
| `backend/app/bmc/ipmi_handler.py` | IPMI 协议操作封装 |
| `backend/app/bmc/redfish_handler.py` | Redfish 协议操作封装 |
| `backend/app/bmc/batch.py` | 批量 BMC 操作 |
| `backend/app/api/bmc.py` | BMC API 路由 |

### 阶段 6 — 节点管理
| 文件 | 职责 |
|------|------|
| `backend/app/node/agent.py` | Agent 本地 CLI 工具 |
| `backend/app/node/ssh.py` | SSH 远程执行 (paramiko) |
| `backend/app/node/monitor.py` | 节点状态监控 |
| `backend/app/api/node.py` | 节点 API 路由 |

### 阶段 7 — 主机管理
| 文件 | 职责 |
|------|------|
| `backend/app/host/ansible.py` | Ansible 集成 |
| `backend/app/host/inventory.py` | 硬件清单 |
| `backend/app/api/host.py` | 主机 API 路由 |

### 阶段 8 — 文件管理
| 文件 | 职责 |
|------|------|
| `backend/app/filemgr/sync.py` | Agent 文件同步 |
| `backend/app/filemgr/repo.py` | 脚本/软件仓库管理 |
| `backend/app/api/filemgr.py` | 文件管理 API 路由 |

### 阶段 9 — 配置模板
| 文件 | 职责 |
|------|------|
| `backend/app/template/preseed.py` | Preseed/Kickstart 模板管理 |
| `backend/app/api/template.py` | 模板 API 路由 |

### 阶段 10 — 仪表盘
| 文件 | 职责 |
|------|------|
| `backend/app/api/dashboard.py` | 仪表盘聚合 API |

### 阶段 11 — Agent CLI
| 文件 | 职责 |
|------|------|
| `backend/cli.py` | Agent 本地 CLI 入口 (供 master SSH 调用) |

### 阶段 12 — WebSocket
| 文件 | 职责 |
|------|------|
| `backend/app/ws.py` | WebSocket 管理器与端点 |

### 阶段 13 — 前端基础
| 文件 | 职责 |
|------|------|
| `frontend/package.json` | 前端依赖 |
| `frontend/vite.config.js` | Vite 构建配置 |
| `frontend/src/main.js` | Vue 应用入口 |
| `frontend/src/App.vue` | 根组件 |
| `frontend/src/router/index.js` | 路由配置 |
| `frontend/src/stores/auth.js` | 认证状态管理 |
| `frontend/src/api/index.js` | API 调用层 |
| `frontend/src/components/Layout.vue` | 布局组件 (侧边栏 + 导航) |

### 阶段 14 — 前端页面
| 文件 | 职责 |
|------|------|
| `frontend/src/views/Login.vue` | 登录页面 |
| `frontend/src/views/Dashboard.vue` | 仪表盘 |
| `frontend/src/views/PXE/Index.vue` | PXE 服务管理 |
| `frontend/src/views/BMC/Index.vue` | BMC 管理 |
| `frontend/src/views/Node/Index.vue` | 节点管理 |
| `frontend/src/views/Host/Index.vue` | 主机管理 |
| `frontend/src/views/FileMgr/Index.vue` | 文件管理 |
| `frontend/src/views/Template/Index.vue` | 配置模板 |

### 阶段 15 — 部署脚本
| 文件 | 职责 |
|------|------|
| `scripts/deploy-ubuntu22.sh` | 一键部署脚本 |

---

## 阶段 1 — 项目基础 (Task 1-15)

**目标:** 可运行的 FastAPI 骨架 + 数据库模型 + 配置系统

### Task 1: 创建后端目录结构和 requirements.txt
- 创建 `backend/app/` 及其子目录
- 创建 `backend/tests/` 目录 (含 `__init__.py`)
- 写入 `backend/requirements.txt`:
  ```
  fastapi==0.115.0
  uvicorn==0.32.0
  sqlalchemy==2.0.35
  pydantic==2.9.0
  pydantic-settings==2.5.0
  python-jose[cryptography]==3.3.0
  passlib[bcrypt]==1.7.4
  cryptography==43.0.0
  paramiko==3.5.0
  python-ipmi==1.0.6
  redfish-rest-client==2.2.0
  bcrypt==4.2.0
  python-multipart==0.0.12
  websocket-client==1.8.0
  pytest==8.3.0
  httpx==0.27.0
  ```

### Task 2: 实现配置管理 `backend/app/config.py`
- 使用 `pydantic-settings` 读取环境变量和配置文件
- 字段: `app_mode` (master/agent), `db_path`, `jwt_secret`, `jwt_expire_minutes`, `fernet_key_path`, `ssh_key_path`, `log_dir`, `tftp_root`, `images_dir`, `files_dir`
- 默认值: 部署路径 `/opt/pxe/` 下的子目录
- 测试: 验证默认配置加载

### Task 3: 实现数据库连接 `backend/app/database.py`
- SQLite 引擎 (带 `check_same_thread=False`)
- 会话工厂 `SessionLocal`
- `get_db` 依赖注入
- `init_db()` 创建所有表
- 写入时 WAL 模式优化
- 测试: 验证表创建成功

### Task 4: 实现数据模型 `backend/app/models.py`
- 实现所有 10 个模型: Node, BmcInfo, Host, PxeConfig, IsoImage, InstallTask, InstallReport, FileInfo, Template, User
- 每个模型包含: 字段定义、关联关系、创建/更新时间戳
- 用户密码使用 bcrypt 哈希存储 (setter 自动哈希)
- BMC 密码使用 Fernet 加密存储 (property getter/setter)
- 测试: 创建每个模型的实例并验证

### Task 5: 实现 FastAPI 应用入口 `backend/app/main.py`
- 创建 `app = FastAPI(title="PXE Manager")`
- 启动事件: 初始化数据库
- CORS 中间件 (配置允许的前端域名)
- 注册 API 路由前缀 `/api/v1`
- 测试: 启动应用，访问根路径返回版本信息

### Task 6: 实现统一错误处理
- 在 `main.py` 中添加异常处理器
- 自定义 `PxeException` 类: code, message
- 响应格式: `{"success": false, "error": {"code": "...", "message": "..."}}`
- 测试: 触发异常验证响应格式

### Task 7: 实现日志配置 `backend/app/utils/logs.py`
- 配置 Python logging
- 日志目录: `/opt/pxe/logs/`
- 按日期轮转，保留 30 天
- 同时输出到 stdout (开发模式) 和文件 (生产模式)
- 测试: 写入日志并验证文件创建

### Task 8: 可运行验证
- 运行 `uvicorn backend.app.main:app --reload`
- 确认服务启动无报错
- 确认 SQLite 数据库文件创建
- 提交

### Task 9-15: 测试覆盖
- `tests/test_config.py` — 配置加载测试
- `tests/test_database.py` — 数据库连接测试
- `tests/test_models.py` — 模型创建/关联测试
- `tests/test_error.py` — 错误响应格式测试
- 运行 `pytest` 确认全部通过
- 提交

---

## 阶段 2 — 认证系统 (Task 16-25)

**目标:** 完整的 JWT 认证 + 角色权限控制

### Task 16: 实现 JWT 处理 `backend/app/auth/jwt_handler.py`
- `create_token(user_id, role)` — 签发 JWT (HS256, 24h 有效期)
- `verify_token(token)` — 验证并返回 payload
- `get_password_hash(password)` — bcrypt 哈希
- `verify_password(password, hashed)` — bcrypt 验证
- 测试: 签发 → 验证 → 过期 → 无效签名

### Task 17: 实现角色权限 `backend/app/auth/roles.py`
- 角色枚举: `admin`, `operator`, `readonly`
- 权限矩阵:
  ```
  路由前缀         | admin | operator | readonly
  /auth/*          |   Y   |    Y     |    Y
  /dashboard       |   Y   |    Y     |    Y
  /pxe/*           |   Y   |    Y     |    N
  /bmc/*           |   Y   |    Y     |    N
  /node/*          |   Y   |    Y     |    Y
  /host/*          |   Y   |    Y     |    Y
  /file/*          |   Y   |    Y     |    N
  /template/*      |   Y   |    N     |    N
  DELETE /*        |   Y   |    N     |    N
  ```
- `check_permission(role, route, method)` — 权限检查函数
- 测试: 每个角色访问每个路由的权限验证

### Task 18: 实现依赖注入 `backend/app/auth/deps.py`
- `get_current_user(token: str = Depends(...))` — 从 Bearer token 获取当前用户
- `require_role(*roles)` — 角色校验依赖
- 测试: 有效 token / 无效 token / 过期 token / 无 token

### Task 19: 实现认证 API `backend/app/api/auth.py`
- `POST /auth/login` — 用户名密码登录，返回 JWT
- `GET /auth/profile` — 获取当前用户信息
- `POST /auth/logout` — 登出 (前端清除 token)
- 登录速率限制: 5 次/分钟 (使用内存计数器)
- 首次启动自动创建默认 admin 用户 (用户名: admin, 密码: admin123，首次登录强制修改)
- 测试: 登录 → 获取 profile → 登出 → 无效凭证

### Task 20: 注册认证路由到 main.py
- `app.include_router(auth_router, prefix="/api/v1")`
- 运行 `pytest tests/test_auth.py`
- 提交

---

## 阶段 3 — 工具层 (Task 21-25)

**目标:** Systemd 服务控制 + 日志工具

### Task 21: 实现 Systemd 工具 `backend/app/utils/systemd.py`
- `systemctl(action, service)` — 封装 systemctl 命令 (start/stop/restart/status/enable/disable)
- `is_active(service)` — 检查服务是否运行
- `get_service_status(service)` — 获取服务详细信息
- 使用 `subprocess.run()` + `check=True`，超时 30 秒
- 测试: Mock subprocess，验证正确调用

### Task 22: 验证工具层
- 运行 `pytest` 确认全部通过
- 提交

---

## 阶段 4 — PXE 服务管理 (Task 23-35)

**目标:** 完整的 PXE 服务配置与管理

### Task 23: 实现 dnsmasq 配置 `backend/app/pxe/dnsmasq.py`
- `generate_config(interface, dhcp_range, tftp_server, mac_filters)` — 生成 dnsmasq.conf 内容
- `apply_config(content)` — 写入 `/etc/dnsmasq.conf` 并重启服务
- `get_config()` — 读取当前配置
- `add_mac_filter(mac, filename)` — 添加 MAC 地址到引导文件映射
- `remove_mac_filter(mac)` — 移除 MAC 过滤规则
- 配置模板支持: 基于 Jinja2 或字符串格式化
- 测试: 生成配置 → 验证语法正确性

### Task 24: 实现 TFTP 管理 `backend/app/pxe/tftp.py`
- `setup_tftp(root_dir)` — 初始化 TFTP 根目录结构
- `get_status()` — 检查 TFTP 服务状态
- `start()/stop()/restart()` — 服务控制
- `list_files(path)` — 列出 TFTP 目录文件
- 测试: 验证目录结构创建

### Task 25: 实现 iPXE 引导菜单 `backend/app/pxe/ipxe.py`
- `generate_menu(isos, hosts)` — 根据 ISO 镜像和主机列表生成 iPXE 菜单
- 支持按 MAC 地址定制菜单项
- 模板: 标准 Ubuntu 22.04 安装菜单 + 自定义选项
- `write_menu(content)` — 写入引导文件
- 测试: 生成菜单 → 验证 iPXE 语法

### Task 26: 实现 ISO 镜像管理 `backend/app/pxe/iso.py`
- `list_images(node_id)` — 列出 ISO 镜像
- `register_image(name, path, arch, node_id)` — 注册镜像到数据库
- `remove_image(image_id)` — 移除镜像
- `get_kernel_and_initrd(path)` — 从 ISO 提取内核和 initrd 路径
- 测试: 镜像注册 → 列出 → 移除

### Task 27: 实现安装任务 `backend/app/pxe/tasks.py`
- `create_task(host_id, iso_id, template_id, node_id)` — 创建安装任务
- `update_progress(task_id, progress)` — 更新进度
- `complete_task(task_id, success, duration, error)` — 完成任务并生成报告
- `get_task(task_id)` / `list_tasks()` — 查询任务
- `retry_task(task_id)` — 重试失败任务
- 任务状态机: pending → running → completed/failed
- 测试: 创建任务 → 更新状态 → 完成 → 验证报告

### Task 28: 实现 PXE API 路由 `backend/app/api/pxe.py`
- `GET /pxe/config` — 获取当前 PXE 配置
- `PUT /pxe/config` — 更新 PXE 配置 (自动应用)
- `GET /pxe/services` — 获取服务状态 (dnsmasq, TFTP)
- `POST /pxe/services/{name}/control` — 服务控制 (start/stop/restart)
- `GET /pxe/images` — 列出 ISO 镜像
- `POST /pxe/images` — 注册 ISO 镜像
- `GET /pxe/tasks` / `GET /pxe/tasks/{id}` — 安装任务查询
- `POST /pxe/tasks` — 创建安装任务
- `POST /pxe/tasks/{id}/retry` — 重试任务
- `GET /pxe/reports/{task_id}` — 安装报告
- 所有路由添加角色权限检查
- 测试: 每个 API 端点的集成测试

### Task 29: 注册 PXE 路由到 main.py
- 运行 `pytest tests/test_pxe.py`
- 提交

### Task 30-35: 测试覆盖
- `tests/test_dnsmasq.py` — 配置生成验证
- `tests/test_ipxe.py` — 引导菜单语法验证
- `tests/test_iso.py` — ISO 管理 CRUD
- `tests/test_tasks.py` — 任务状态机
- `tests/test_pxe_api.py` — API 端点集成测试
- 运行 `pytest` 确认全部通过
- 提交

---

## 阶段 5 — BMC 管理 (Task 36-45)

**目标:** BMC/IPMI/Redfish 电源操作

### Task 36: 实现 IPMI 处理器 `backend/app/bmc/ipmi_handler.py`
- 封装 python-ipmi 库
- `get_power_status(bmc_info)` — 查询电源状态
- `power_on/off/restart/cycle(bmc_info)` — 电源操作
- `get_sensor_data(bmc_info)` — 获取传感器数据
- 连接超时: 10 秒，重试 1 次
- 测试: Mock python-ipmi 连接

### Task 37: 实现 Redfish 处理器 `backend/app/bmc/redfish_handler.py`
- 封装 redfish-rest-client 库
- 相同接口: `get_power_status()`, `power_on/off/restart()`
- 自动检测: 优先 Redfish，不支持则回退到 IPMI
- 测试: Mock Redfish 连接

### Task 38: 实现批量操作 `backend/app/bmc/batch.py`
- `batch_power_action(bmc_ids, action)` — 批量电源操作
- 使用 `ThreadPoolExecutor` 并行执行 (最大并发 10)
- 返回: `{bmc_id: {"success": bool, "error": str}}`
- 通过 WebSocket 推送逐个结果 (见阶段 12)
- 测试: 并行执行多个操作

### Task 39: 实现 BMC API 路由 `backend/app/api/bmc.py`
- `GET /bmc` — 列出 BMC (支持筛选: 状态、协议)
- `POST /bmc` — 单个添加 BMC
- `POST /bmc/batch` — 批量添加 (支持 CSV 格式: hostname,ip,user,pass,protocol)
- `POST /bmc/{id}/power/{action}` — 电源操作 (on/off/restart/cycle)
- `GET /bmc/stats` — BMC 统计信息
- 所有路由添加角色权限检查
- 测试: CRUD + 批量操作

### Task 40: 注册 BMC 路由到 main.py
- 运行 `pytest tests/test_bmc.py`
- 提交

### Task 41-45: 测试覆盖
- `tests/test_ipmi_handler.py` — IPMI 操作 Mock 测试
- `tests/test_redfish_handler.py` — Redfish 操作 Mock 测试
- `tests/test_batch.py` — 批量操作并发测试
- `tests/test_bmc_api.py` — API 端点集成测试
- 运行 `pytest` 确认全部通过
- 提交

---

## 阶段 6 — 节点管理 (Task 46-55)

**目标:** Master 通过 SSH 管理 Agent 节点

### Task 46: 实现 SSH 远程执行 `backend/app/node/ssh.py`
- 封装 paramiko
- `connect(host, port, key_path)` — SSH 连接
- `exec_command(host, command, timeout=30)` — 执行远程命令
- `exec_batch(hosts, command)` — 批量执行
- 连接池: 复用 SSH 连接 (避免频繁握手)
- 测试: Mock paramiko

### Task 47: 实现 Agent CLI 工具 `backend/cli.py`
- 使用 argparse 实现 CLI 入口
- 命令: `status`, `pxe-config`, `bmc-list`, `bmc-power`, `install-task`, `file-sync`, `log`
- 输入/输出: JSON 格式 (stdin/stdout)
- 错误: 错误码 + JSON 到 stderr
- 测试: 直接调用 CLI 验证输出格式

### Task 48: 实现节点状态监控 `backend/app/node/monitor.py`
- `check_node_status(node)` — 通过 SSH 检查节点状态
- `check_all_nodes()` — 批量检查所有节点
- 更新数据库中的节点状态和最后心跳时间
- 离线判定: 3 次连续失败标记为 offline
- 测试: Mock SSH 响应

### Task 49: 实现节点 API 路由 `backend/app/api/node.py`
- `GET /node` — 列出节点 (支持筛选)
- `POST /node` — 添加节点 (IP、SSH 密钥)
- `DELETE /node/{id}` — 移除节点
- `POST /node/{id}/check` — 手动检查节点状态
- `GET /node/{id}/ssh` — 获取 SSH 连接信息 (用于终端连接)
- 测试: CRUD + 状态检查

### Task 50: 注册节点路由到 main.py
- 运行 `pytest tests/test_node.py`
- 提交

### Task 51-55: 测试覆盖
- `tests/test_ssh.py` — SSH 连接与命令执行
- `tests/test_monitor.py` — 节点状态检测逻辑
- `tests/test_node_api.py` — API 端点集成测试
- 运行 `pytest` 确认全部通过
- 提交

---

## 阶段 7 — 主机管理 (Task 56-65)

**目标:** 主机列表 + Ansible 集成 + 硬件清单

### Task 56: 实现 Ansible 集成 `backend/app/host/ansible.py`
- 封装 `ansible-core` 或 `ansible-runner`
- `run_playbook(host, playbook, extra_vars)` — 执行 Playbook
- `run_module(host, module, args)` — 执行单个模块
- 输出: 实时 stdout/stderr 捕获
- 测试: Mock ansible 调用

### Task 57: 实现硬件清单 `backend/app/host/inventory.py`
- `get_hardware_info(host)` — 收集硬件信息 (CPU, 内存, 磁盘, 网卡)
- 通过 SSH 执行 `dmidecode`, `lspci`, `lsblk` 等命令
- 返回结构化 JSON
- 测试: Mock 命令输出

### Task 58: 实现主机 API 路由 `backend/app/api/host.py`
- `GET /host` — 列出主机 (支持筛选)
- `POST /host` — 添加主机 (关联节点/BMC)
- `DELETE /host/{id}` — 移除主机
- `GET /host/{id}/hardware` — 获取硬件清单
- `POST /host/{id}/ansible` — 执行 Ansible 命令
- `POST /host/{id}/ssh` — SSH 连接信息
- 测试: CRUD + 硬件信息

### Task 59: 注册主机路由到 main.py
- 运行 `pytest tests/test_host.py`
- 提交

### Task 60-65: 测试覆盖
- `tests/test_ansible.py` — Ansible 操作 Mock 测试
- `tests/test_inventory.py` — 硬件信息收集
- `tests/test_host_api.py` — API 端点集成测试
- 运行 `pytest` 确认全部通过
- 提交

---

## 阶段 8 — 文件管理 (Task 66-75)

**目标:** 文件上传/分类/同步

### Task 66: 实现文件同步 `backend/app/filemgr/sync.py`
- `sync_to_agent(file_ids, node_id)` — 通过 SSH 同步文件到 agent
- 使用 `scp` 或 `sftp` 传输
- 文件完整性: MD5 校验
- 更新数据库中的同步状态
- 测试: Mock SSH 传输

### Task 67: 实现仓库管理 `backend/app/filemgr/repo.py`
- 管理脚本/软件仓库目录
- `list_files(category)` — 按分类列出文件
- `upload_file(file, category)` — 上传文件
- `remove_file(file_id)` — 删除文件
- 支持的分类: script, config, repo
- 测试: 上传 → 列出 → 删除

### Task 68: 实现文件管理 API `backend/app/api/filemgr.py`
- `GET /file` — 列出文件 (支持分类筛选)
- `POST /file/upload` — 上传文件 (multipart/form-data)
- `DELETE /file/{id}` — 删除文件
- `POST /file/sync` — 同步到指定 agent
- `GET /file/{id}/download` — 下载文件
- 测试: 完整文件生命周期

### Task 69: 注册文件管理路由到 main.py
- 运行 `pytest tests/test_filemgr.py`
- 提交

### Task 70-75: 测试覆盖
- `tests/test_sync.py` — 文件同步逻辑
- `tests/test_repo.py` — 仓库管理
- `tests/test_filemgr_api.py` — API 端点集成测试
- 运行 `pytest` 确认全部通过
- 提交

---

## 阶段 9 — 配置模板 (Task 76-85)

**目标:** Preseed/Kickstart/user-data 模板管理

### Task 76: 实现模板管理 `backend/app/template/preseed.py`
- `create_template(name, type, content, defaults)` — 创建模板
- `get_template(id)` — 获取模板
- `list_templates(type)` — 按类型列出
- `update_template(id, **fields)` — 更新模板
- `delete_template(id)` — 删除模板
- `render_template(template_id, variables)` — 渲染模板 (Jinja2)
- 内置模板: Ubuntu 22.04 Preseed (默认分区、默认网络)
- 测试: 创建 → 渲染 → 更新 → 删除

### Task 77: 实现模板 API `backend/app/api/template.py`
- `GET /template` — 列出模板
- `POST /template` — 创建模板
- `GET /template/{id}` — 获取模板
- `PUT /template/{id}` — 更新模板
- `DELETE /template/{id}` — 删除模板
- `POST /template/{id}/render` — 渲染模板 (传入变量)
- 测试: 完整 CRUD + 渲染

### Task 78: 注册模板路由到 main.py
- 运行 `pytest tests/test_template.py`
- 提交

### Task 79-85: 测试覆盖
- `tests/test_preseed.py` — 模板管理逻辑
- `tests/test_render.py` — 模板渲染验证 (Jinja2)
- `tests/test_template_api.py` — API 端点集成测试
- 运行 `pytest` 确认全部通过
- 提交

---

## 阶段 10 — 仪表盘 (Task 86-90)

**目标:** 聚合统计数据和快捷操作

### Task 86: 实现仪表盘 API `backend/app/api/dashboard.py`
- `GET /dashboard` — 聚合查询:
  - 节点统计: 总数、在线、离线
  - 主机统计: 总数、各状态数量
  - BMC 统计: 总数、开机、关机、其他
  - PXE 服务状态: dnsmasq、TFTP
  - 最近安装任务: 最近 5 条
  - 快捷操作: 常用功能链接
- 测试: 验证聚合数据格式

### Task 87: 注册仪表盘路由到 main.py
- 运行 `pytest tests/test_dashboard.py`
- 提交

### Task 88-90: 测试覆盖
- `tests/test_dashboard.py` — 聚合数据验证
- 运行 `pytest` 确认全部通过
- 提交

---

## 阶段 11 — Agent CLI (Task 91-95)

**目标:** 完整的 Agent CLI 工具

### Task 91-93: 实现 Agent CLI `backend/cli.py`
- 实现所有子命令: `status`, `pxe-config`, `bmc-list`, `bmc-power`, `install-task`, `file-sync`, `log`
- JSON 输入/输出协议
- 错误处理: 错误码 + 消息到 stderr
- 与数据库和后端模块集成
- 测试: 每个命令的端到端测试

### Task 94-95: 验证 CLI
- 本地运行每个命令验证
- 模拟 master SSH 调用场景
- 提交

---

## 阶段 12 — WebSocket (Task 96-100)

**目标:** 实时数据推送

### Task 96: 实现 WebSocket 管理器 `backend/app/ws.py`
- `WebSocketManager` 类: 管理活跃连接
- `connect(websocket)` — 注册连接
- `disconnect(websocket)` — 移除连接
- `broadcast(event_type, data)` — 广播消息
- `send_to(user_id, event_type, data)` — 单用户推送
- 消息格式: `{"type": "event_name", "data": {...}}`

### Task 97: 实现 WebSocket 端点
- `WS /ws` — 认证 WebSocket 连接
- `WS /ws/tasks` — 安装任务进度推送
- `WS /ws/bmc` — BMC 批量操作结果推送
- `WS /ws/services` — 服务状态变化推送
- 重连: 客户端断开后自动重连

### Task 98: 集成 WebSocket 到业务流程
- 安装任务: 状态变化时推送
- BMC 批量操作: 逐个推送结果
- 服务状态监控: 变化时推送
- 节点状态: 变化时推送

### Task 99-100: 测试 WebSocket
- 使用 `websockets` 库测试连接
- 验证消息格式和推送时机
- 提交

---

## 阶段 13 — 前端基础 (Task 101-115)

**目标:** Vue 3 + Element Plus 项目骨架

### Task 101: 创建前端项目
- 创建 `frontend/` 目录
- 写入 `frontend/package.json`:
  ```json
  {
    "name": "pxe-manager-frontend",
    "version": "0.1.0",
    "scripts": {
      "dev": "vite",
      "build": "vite build",
      "preview": "vite preview",
      "test": "vitest"
    },
    "dependencies": {
      "vue": "^3.5.0",
      "vue-router": "^4.4.0",
      "pinia": "^2.2.0",
      "element-plus": "^2.9.0",
      "@element-plus/icons-vue": "^2.3.0",
      "axios": "^1.7.0"
    },
    "devDependencies": {
      "@vitejs/plugin-vue": "^5.1.0",
      "vite": "^6.0.0",
      "vitest": "^2.1.0"
    }
  }
  ```

### Task 102: 配置 Vite `frontend/vite.config.js`
- Vue 插件
- API 代理: `/api/v1` → `http://localhost:8000`
- 别名: `@` → `src/`

### Task 103: 创建 Vue 入口 `frontend/src/main.js`
- 注册 Element Plus (中文 locale)
- 注册 Pinia
- 注册 Vue Router

### Task 104: 创建路由配置 `frontend/src/router/index.js`
- 路由表:
  - `/login` — 登录
  - `/` — 仪表盘 (重定向到 `/dashboard`)
  - `/dashboard` — 仪表盘
  - `/pxe` — PXE 服务
  - `/bmc` — BMC 管理
  - `/node` — 节点管理
  - `/host` — 主机管理
  - `/file` — 文件管理
  - `/template` — 配置模板
- 路由守卫: 未登录 → 跳转 /login

### Task 105: 创建 API 调用层 `frontend/src/api/index.js`
- Axios 实例 + 请求/响应拦截器
- JWT token 自动附加
- 401 响应 → 清除 token → 跳转登录
- 统一错误处理
- 导出各模块 API 方法: `authApi`, `dashboardApi`, `pxeApi`, `bmcApi`, `nodeApi`, `hostApi`, `fileApi`, `templateApi`

### Task 106: 创建认证状态 `frontend/src/stores/auth.js`
- Pinia store: `user`, `token`, `role`
- `login(username, password)` — 登录
- `logout()` — 登出
- `isLoggedIn()` — 检查登录状态
- 本地存储 token (localStorage)

### Task 107: 创建布局组件 `frontend/src/components/Layout.vue`
- 侧边栏导航 (Element Plus Menu)
- 顶部栏: 用户名、退出
- 路由视图: `<router-view />`
- 根据角色显示/隐藏菜单项

### Task 108: 创建根组件 `frontend/src/App.vue`
- 条件渲染: 已登录 → Layout，未登录 → `<router-view />` (仅登录页)

### Task 109: 创建登录页 `frontend/src/views/Login.vue`
- Element Plus 表单: 用户名 + 密码
- 登录按钮 → 调用 authApi.login
- 成功 → 跳转 dashboard
- 失败 → 显示错误信息

### Task 110: 启动前端验证
- `npm install`
- `npm run dev`
- 验证开发服务器启动
- 验证登录页面显示
- 提交

### Task 111-115: 前端测试
- `tests/auth.test.js` — 认证流程
- `tests/api.test.js` — API 拦截器
- 运行 `vitest` 确认通过
- 提交

---

## 阶段 14 — 前端页面 (Task 116-150)

**目标:** 所有管理页面

### Task 116-120: 仪表盘 `frontend/src/views/Dashboard.vue`
- 统计卡片: 节点、主机、BMC (Element Plus Card + Statistic)
- 服务状态: dnsmasq/TFTP (Switch 组件)
- 最近任务: 表格展示
- 快捷操作: 按钮组
- WebSocket 连接: 实时更新
- 测试: 验证 API 调用和数据展示

### Task 121-125: PXE 服务 `frontend/src/views/PXE/Index.vue`
- 服务状态: dnsmasq/TFTP 启停控制
- 配置编辑: 代码编辑器 (monaco-editor 或 textarea)
- ISO 镜像列表: 上传、删除
- 安装任务: 创建、进度显示、重试
- MAC 过滤规则: 添加、删除
- 日志查看: 日志文件展示
- 测试: 验证 CRUD 操作

### Task 126-130: BMC 管理 `frontend/src/views/BMC/Index.vue`
- BMC 列表: 表格 (支持筛选、排序)
- 批量添加: 对话框 + CSV 输入
- 电源操作: 行内按钮 (on/off/restart)
- 批量操作: 选择 → 操作 → 实时进度
- 统计信息: 开机/关机/其他
- WebSocket: 批量操作结果推送
- 测试: 验证列表和批量操作

### Task 131-135: 节点管理 `frontend/src/views/Node/Index.vue`
- 节点列表: 表格 (IP、状态、最后心跳)
- 添加节点: 对话框表单
- 状态检查: 行内按钮
- SSH 连接: 终端集成 (xterm.js)
- WebSocket: 节点状态实时更新
- 测试: 验证 CRUD 和状态检查

### Task 136-140: 主机管理 `frontend/src/views/Host/Index.vue`
- 主机列表: 表格 (支持筛选)
- 添加主机: 对话框表单 (关联节点/BMC)
- 硬件清单: 抽屉展示
- Ansible 操作: 对话框输入命令
- SSH 连接: 终端集成
- 测试: 验证 CRUD 和硬件信息

### Task 141-145: 文件管理 `frontend/src/views/FileMgr/Index.vue`
- 文件列表: 树形/表格展示
- 上传: 拖拽上传 (Element Plus Upload)
- 分类筛选: Tabs 组件
- 同步: 选择 agent → 同步
- 下载/删除: 行内操作
- 测试: 验证文件上传和同步

### Task 146-150: 配置模板 `frontend/src/views/Template/Index.vue`
- 模板列表: 表格 (按类型分组)
- 创建/编辑: 代码编辑器
- 渲染预览: 输入变量 → 预览结果
- 删除: 确认对话框
- 测试: 验证 CRUD 和渲染

---

## 阶段 15 — 一键部署脚本 (Task 151-160)

**目标:** `deploy-ubuntu22.sh` 自动化部署

### Task 151: 脚本框架 `scripts/deploy-ubuntu22.sh`
- 参数解析: `master` | `agent`
- root 权限检查
- Ubuntu 22.04 版本检查

### Task 152: 依赖安装
- `apt-get install` dnsmasq, tftp-hpa, ipxe, openssh-server
- Python 3.10+ 和 pip 安装
- Node.js 20+ 和 npm 安装
- `pip install -r requirements.txt`
- `cd frontend && npm install && npm run build`

### Task 153: 目录结构创建
- `/opt/pxe/data/` — 数据库
- `/opt/pxe/images/` — ISO 镜像
- `/opt/pxe/files/` — 文件管理
- `/opt/pxe/logs/` — 日志
- `/opt/pxe/tftpboot/` — TFTP 根目录
- `/opt/pxe/tftpboot/ipxe/` — iPXE 引导文件
- `/opt/pxe/tftpboot/pxelinux.cfg/` — PXE 配置

### Task 154: 配置文件生成
- 生成 `/opt/pxe/backend/app/config.py` 的本地配置覆盖
- 生成 Fernet 密钥: `/root/.pxe/secret.key`
- 生成 JWT 密钥

### Task 155: Systemd 服务配置
- `pxe-backend.service` — FastAPI 服务 (uvicorn)
- `pxe-frontend.service` — Vite/Nginx 前端静态服务
- `systemctl enable --now pxe-backend`
- `systemctl enable --now pxe-frontend`

### Task 156: PXE 服务初始化
- 初始化 dnsmasq 默认配置
- 初始化 TFTP 目录结构
- 下载 iPXE 引导文件 (ipxe.bin)
- 生成默认 iPXE 菜单

### Task 157: 数据库初始化
- 运行 `init_db()` 创建所有表
- 创建默认 admin 用户
- Agent 模式: 创建本地节点记录

### Task 158: 防火墙配置
- 开放端口: 67/udp (DHCP), 69/udp (TFTP), 80/tcp (HTTP), 8000/tcp (API), 5173/tcp (前端)
- `ufw allow` 规则
- Agent 模式额外开放 iPXE 所需端口

### Task 159: Master 模式额外配置
- SSH 密钥生成: `ssh-keygen -t ed25519`
- 配置 `~/.ssh/config` 用于 agent 连接
- 初始化 master 节点数据库

### Task 160: 部署验证
- 检查服务状态: `systemctl is-active pxe-backend`
- 检查 API: `curl http://localhost:8000/api/v1/health`
- 输出部署信息: 访问地址、默认账号
- 提交

---

## 阶段 16 — 最终集成测试 (Task 161-170)

**目标:** 端到端测试 + 代码覆盖

### Task 161-165: E2E 测试 (Playwright)
- 登录 → 仪表盘 → 验证数据
- 创建 PXE 配置 → 验证配置应用
- 添加 BMC → 批量操作 → 验证结果
- 创建安装任务 → 跟踪进度 → 验证报告
- 文件上传 → 同步 → 验证同步状态

### Task 166: 代码覆盖率报告
- `pytest --cov=backend/app tests/`
- 核心逻辑覆盖率 80%+
- API 端点 100% 覆盖

### Task 167: 最终清理
- 移除调试代码
- 检查 .gitignore
- 确保无敏感信息提交

### Task 168-170: 提交与收尾
- 最终 `pytest` 全量运行
- 提交所有更改
- 验证部署脚本

---

## 执行顺序与依赖

```
阶段 1 (基础)
  └── 阶段 2 (认证)
        └── 阶段 3 (工具层)
              └── 阶段 4 (PXE 服务) ← 可与阶段 5 并行
              └── 阶段 5 (BMC)     ← 可与阶段 4 并行
              └── 阶段 6 (节点)
              └── 阶段 7 (主机)
              └── 阶段 8 (文件)
              └── 阶段 9 (模板)
                    └── 阶段 10 (仪表盘)
                          └── 阶段 11 (Agent CLI)
                                └── 阶段 12 (WebSocket)
                                      └── 阶段 13 (前端基础)
                                            └── 阶段 14 (前端页面)
                                                  └── 阶段 15 (部署脚本)
                                                        └── 阶段 16 (集成测试)
```

**可并行执行的阶段:**
- 阶段 4/5/6/7/8/9 可并行 (都依赖阶段 3)
- 阶段 13/14 可在阶段 10 之后并行 (前端不依赖后端完整实现)

## 提交策略

- 每个阶段完成后提交一次 (保持独立可运行)
- 提交信息格式: `<模块>: <描述>`
  - `基础: 初始化 FastAPI 项目和数据模型`
  - `认证: 实现 JWT 认证和角色权限`
  - `PXE: 实现 PXE 服务管理`
  - ...
