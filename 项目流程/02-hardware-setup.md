# 2. 硬件与系统环境

## 硬件配置

| 组件 | 型号 | 说明 |
|------|------|------|
| 显卡 | NVIDIA RTX 5070 12GB | Blackwell 架构，训练 SmolVLA |
| CPU | AMD Ryzen 7 3700X (8核16线程) | |
| 内存 | 96GB DDR4 3200MHz | |
| 主板 | B450M | 老平台，需更新 BIOS 才支持 RTX 5070 |
| 存储 | 移动固态硬盘 (USB 3.0) | Ubuntu 22.04 便携系统 |

## Ubuntu 移动硬盘系统

选择将系统安装在移动固态硬盘上，主要考虑：
- 在多台电脑之间便携切换
- 系统与数据独立于主机，不怕主机系统崩溃
- 保留完整 GPU 驱动能力

### 通过虚拟机安装系统到移动固态硬盘

一开始尝试用 U 盘启动盘直接安装，但遇到了两个关键问题：

1. **显卡不兼容导致无法开机**：RTX 5070 新显卡与老主板 B450M 默认 BIOS 不兼容，U 盘启动后无法正常进入安装界面或安装完成后无法启动
2. **磁盘选择容易出错**：安装界面会列出所有硬盘（包括 Windows 系统盘），容易误操作导致 Windows 系统无法正常运行

因此最终采用的方案是：**在虚拟机中先把系统安装到移动固态硬盘**。具体操作步骤如下。

#### 操作流程

1. 在 Windows 上安装虚拟机软件（如 VMware Workstation 或 VirtualBox）
2. 将移动固态硬盘连接到虚拟机，挂载为虚拟机的物理磁盘
3. 在虚拟机中用 Ubuntu 22.04 ISO 启动，安装到该移动固态硬盘
4. 安装完成后，在虚拟机中完成以下配置（这些不需要实机环境）：
   - 替换 apt 源（阿里云镜像）
   - 安装 OpenCode 终端版（用于后续自动安装基础环境）
   - 用 OpenCode 安装基础工具（git, vim, htop, tmux, curl, wget 等）
   - 安装并配置 SSH server（开机自启）
   - 安装 Miniconda、配置 conda 环境
   - 配置 GRUB（添加 nomodeset 参数，防止首次实机启动黑屏）
   - 禁用自动更新和系统休眠
5. 虚拟机中能装的都装好之后，重启电脑，通过 BIOS 启动菜单选择从移动固态硬盘直接启动 Ubuntu 22.04
6. 实机启动成功后，再安装 NVIDIA 驱动等需要真实硬件的组件

> 网上可以搜到 "虚拟机安装 Ubuntu 到物理硬盘 / 移动硬盘" 的相关教程，推荐参考。

#### 首次实机启动

首次用移动固态硬盘在实机上启动时，并不会直接进入桌面 GUI：

1. 启动时按对应键进入 BIOS 启动菜单（F12/F2/Del，不同品牌不同）
2. 选择从 USB / UEFI 移动硬盘启动
3. **只能进入命令行模式**：因为还没装 NVIDIA 驱动，GRUB 已预先配置了 `nomodeset` 参数，桌面环境无法启动，只能以 tty 命令行登录
4. 此时 SSH server 已预先配置好，通过网络从另一台电脑 SSH 远程操作，在命令行下安装 NVIDIA 驱动
5. NVIDIA 驱动安装完成后重启，桌面 GUI 才能正常亮起

> 从虚拟机到真机并不是一帆风顺的——首次只能进命令行、靠 SSH 远程开发是必要手段。而且即使装了驱动亮了 GUI，后面仍然花了很长时间排查，最终才发现是 BIOS 版本过旧导致的问题。详见踩坑记录。

### 安装流程（实机启动后的配置顺序）

1. **确认 GRUB nomodeset**：防止未装驱动前黑屏
2. **替换镜像源**：官方源 → 阿里云镜像，加速国内下载
3. **安装 NVIDIA 驱动**（见下方 NVIDIA 驱动安装）
4. **配置 SSH**：确保 openssh-server 已开机自启，方便后续远程操作
5. **禁用自动更新**：`systemctl disable apt-daily`，避免后台 IO 抢占移动硬盘
6. **禁用系统休眠**：`systemctl mask sleep.target`，移动硬盘休眠后 USB 断电无法恢复
7. **安装 Miniconda** → 创建 conda 环境（如在虚拟机中未完成）
8. **安装 PyTorch + CUDA**
9. **安装仿真环境**（MuJoCo）
10. **创建项目工作目录结构**

### 软件安装清单

**系统基础工具**：

```bash
sudo apt update
sudo apt install -y git vim htop tmux tree net-tools iputils-ping curl wget
```

以上基础工具也可以在虚拟机阶段通过 OpenCode 终端版自动安装。

**Python 环境（Miniconda）**：

不使用系统 Python，用 conda 隔离环境：

```bash
# 下载 Miniconda（官网获取最新链接）
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
# 安装路径默认 ~/miniconda3

# 重启终端后验证
conda --version
```

### 远程开发工具链

由于 Ubuntu 桌面环境下中文输入法安装配置繁琐且效果一般，本项目采用**远程开发**模式：Ubuntu 机器负责所有需要真实 GPU / 硬件的运算，日常代码编写、文档编辑、查资料等在另一台电脑上通过远程方式完成。

#### 远程开发方式选择：Trae

选择 [Trae](https://www.trae.ai/) 作为远程开发 IDE，原因：

| 优势 | 说明 |
|------|------|
| 免费 | 无使用成本 |
| AI 能力够用 | 基础代码补全和问答满足日常开发需求 |
| "添加到对话" 功能 | 可以选中代码或文件加入对话，方便让 AI 理解上下文、学习代码 |
| 文件管理系统 | 方便浏览项目目录结构和查看文件 |
| 远程 SSH 支持 | 通过 SSH 直接连接到 Ubuntu 机器进行远程开发 |

> 如果有条件，使用 Claude Code 或 Codex 当然更好。

#### Ubuntu 端安装的 GUI 软件

虽然日常开发通过远程进行，Ubuntu 实机上仍安装了几个 GUI 软件方便本地操作：

| 软件 | 用途 | 备注 |
|------|------|------|
| **Obsidian** | Markdown 笔记 / 文档管理 | 强烈推荐。本项目所有文档都在 Obsidian 中编写。可以方便地查看和管理代码文件、文档。当需要在实机上执行某些代码时，可以从 Obsidian 中复制出来到本地终端运行 |
| **VS Code** | 代码编辑器 | 备用的本地编辑器 |
| **Trae** | AI IDE | 备用的本地 AI 开发工具 |
| **LocalSend** | 局域网文件传输 | 方便在笔记本和 Ubuntu 台式机之间传文件。比如网络不稳定时可以在笔记本上下载模型 / 项目 zip 包（Issac Lab、LeRobot 等参考项目），再通过 LocalSend 传到 Ubuntu 机器上 |

#### OpenCode 终端版

在虚拟机阶段优先安装 OpenCode 终端版，之后很多基础环境可以借助 OpenCode 的 AI 能力自动安装配置，大幅减少手动操作。

### 网络配置

国内网络环境下需要解决 GitHub、HuggingFace 等国外服务的访问问题：

- **apt 源**：替换为阿里云镜像（`mirrors.aliyun.com`）
- **GitHub 访问**：视网络情况配置代理或使用镜像
- **HuggingFace 模型下载**：可通过镜像站或先在网络好的笔记本上下载后，用 LocalSend 传到 Ubuntu 机器

### 其他工具（可选）

**Docker（可选，本项目未实际使用）**：

```bash
sudo apt install -y docker.io docker-compose-v2
sudo systemctl start docker
sudo systemctl enable docker

# 配置镜像加速（国内）
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<EOF
{
  "registry-mirrors": ["https://docker.1ms.run"]
}
EOF
sudo systemctl restart docker
```

**Isaac SIM（评估后未使用）**：需要 Python 3.10/3.11（本项目使用 3.12）且需要 NVIDIA Omniverse 账户，本项目是实机开发，未使用仿真。

### 工作目录结构

```bash
mkdir -p /home/jer/ws/workspace/projects   # 代码仓库
mkdir -p /home/jer/ws/workspace/datasets   # 数据集
mkdir -p /home/jer/ws/workspace/models     # 模型权重
mkdir -p /home/jer/ws/docs                 # 项目文档
```

### 环境变量配置

在 `~/.bashrc` 中添加：

```bash
# conda
source ~/miniconda3/etc/profile.d/conda.sh

# CUDA
export PATH=/usr/local/cuda/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
```

### 常用别名

```bash
# ~/.bashrc 中添加
alias ll='ls -lah'
alias gs='git status'
alias gc='git commit -m'
alias update='sudo apt update && sudo apt upgrade -y'
alias ports='netstat -tulanp'
```

### 系统备份与迁移

导出已安装软件包列表，方便在全新系统上恢复：

```bash
# 导出
dpkg --get-selections > packages.list

# 导入（在全新系统上）
sudo dpkg --set-selections < packages.list
sudo apt-get dselect-upgrade
```

## BIOS 更新

由于 RTX 5070 是 Blackwell 新架构，老主板默认 BIOS 无法识别该显卡，必须先更新 BIOS 固件。

### 操作步骤

1. 访问主板厂商官网，下载对应型号的最新 BIOS 固件
2. 将 BIOS 文件放入 FAT32 格式 U 盘根目录
3. 重启进入 BIOS，使用内置更新工具（EZ Flash / M-Flash / Q-Flash）刷入
4. 更新完成后恢复默认设置，重新配置：
   - 开启 **Resizable BAR**（或 Above 4G Decoding）
   - 关闭 **SecureBoot**
   - 部分主板关闭 **CSM**（兼容模式），使用纯 UEFI 启动
5. 保存并重启

## NVIDIA 驱动安装

RTX 5070 的驱动安装与旧显卡有两处关键差异：必须使用 open 内核模块版本，且驱动最低版本 ≥ 550。

### 安装步骤

```bash
# 1. 添加 PPA 源
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update

# 2. 安装 open 版驱动（注意包名 -open 后缀）
sudo apt install -y nvidia-driver-580-open

sudo reboot
```

### 验证

```bash
nvidia-smi                    # 应显示 RTX 5070 + Driver 580.126.20 + CUDA 13.0
lspci | grep -i nvidia        # 确认 PCIe 设备被识别
```

驱动安装成功后，移除 GRUB 中的 `nomodeset` 参数，恢复正常分辨率。

## CUDA + PyTorch

| 组件 | 版本 |
|------|------|
| NVIDIA 驱动 | 580.126.20 (open) |
| CUDA | 13.0 |
| PyTorch | 2.10.0+cu128 |

```bash
python -c "import torch; print(torch.cuda.is_available())"  # 应输出 True
```