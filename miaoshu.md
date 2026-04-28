## 项目概述

PXE Manager 是一个基于 Web 的 PXE 网络启动分布式（master/agent）管理系统，用于自动化部署和管理服务器操作系统安装。

目标在网页上完成pxe操作配置，部署环境定位ubuntu22.04-live-server系统

### 核心功能

1. **仪表盘** - 节点,主机,bmc等统计、系统状态、常用操作快捷跳转等
2. **PXE 服务** - dnsmasq服务控制、 iPXE 引导菜单、配置查看/编辑、dhcp配置、iso镜像、安装任务、安装报告、MAC过滤、日志查看
3. **节点管理** - 集群节点信息、状态监控、节点控制、远程ssh等
4. **BMC 管理** - BMC列表、BMC统计、单个/批量添加bmc、状态显示等、bmc电源操作等
5. **配置模板** - user-data/Kickstart/Preseed 模板管理等
6. **文件管理** - 文件分类、agent同步选项、脚本软件仓库可供pxe使用等
7. **主机管理** - 主机列表、远程ssh连接、集成ansible可操作远程主机、硬件清单等


#### Ubuntu 22.04 一键部署

```
# Master 模式（管理节点统计并管理agent节点）
sudo bash scripts/deploy-ubuntu22.sh master

# Agent 模式（PXE 服务节点）
sudo bash scripts/deploy-ubuntu22.sh agent
```
#### 备注
项目文档注释及聊天全程使用中文
需以agent节点为主，agent节点可完全离线运行且不影响功能，镜像和文件本地存放
master节点以全方位统计展示数据、远程控制agent节点、文件同步、远程连接为主
