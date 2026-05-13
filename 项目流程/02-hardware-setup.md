# 2. 硬件与系统环境

## 硬件配置

| 组件 | 型号 | 说明 |
|------|------|------|
| 显卡 | NVIDIA RTX 5070 12GB | Blackwell 架构，训练 SmolVLA |
| CPU | AMD Ryzen 7 3700X (8核16线程) | |
| 内存 | 96GB DDR4 3200MHz | |
| 主板 | X570/B450 等老平台 | 需更新 BIOS 才支持 RTX 5070 |
| 存储 | 移动固态硬盘 (USB 3.0) | Ubuntu 22.04 便携系统 |

## Ubuntu 移动硬盘系统

选择将系统安装在移动固态硬盘上，主要考虑：
- 在多台电脑之间便携切换
- 系统与数据独立于主机，不怕主机系统崩溃
- 保留完整 GPU 驱动能力

### 制作启动盘并安装到移动固态硬盘

#### 准备工作

1. **准备材料**：
   - 移动固态硬盘（容量 ≥ 256GB，本项目使用 USB 3.0 接口）
   - 另一台能正常上网的电脑，用于下载 Ubuntu ISO 和制作启动盘
   - 一个 ≥ 8GB 的 U 盘（作为启动盘）

2. **下载 Ubuntu 22.04 ISO**：
   从 https://releases.ubuntu.com/22.04/ 下载 `ubuntu-22.04.5-desktop-amd64.iso`

3. **制作启动 U 盘**：使用 Rufus（Windows）或 balenaEtcher（跨平台）将 ISO 写入 U 盘

#### 安装步骤

1. 将启动 U 盘和目标移动固态硬盘同时插入电脑
2. 重启电脑，进入 BIOS 选择从 U 盘启动
3. 进入 Ubuntu 安装程序：
   - 语言选择 English
   - **安装类型选 "Erase disk and install Ubuntu"**
   - **关键：在磁盘选择界面，务必选移动固态硬盘（不是主机内置硬盘！）**
   - 可以通过硬盘容量来区分（移动硬盘容量通常与内置盘不同）
4. 设置用户名和密码：
   - 用户名：`jer`
   - 计算机名：自定
5. 等待安装完成，重启

#### 首次启动

由于是移动硬盘系统，首次插入不同电脑时可能遇到问题：

1. **启动时按对应键进入 BIOS 启动菜单**（F12/F2/Del，不同品牌不同）
2. 选择从 USB / UEFI 移动硬盘启动
3. 如果黑屏，参考下方 GRUB nomodeset 配置

### 安装流程（系统安装后的配置顺序）

1. **配置 GRUB**：添加 `nomodeset` 参数防止不兼容显卡黑屏
2. **替换镜像源**：官方源 → 阿里云镜像，加速国内下载
3. **安装基础工具**：git, vim, htop, tmux, tree, net-tools, curl, wget
4. **配置 SSH**：安装 openssh-server，开机自启，方便远程操作
5. **禁用自动更新**：`systemctl disable apt-daily`，避免后台 IO 抢占移动硬盘
6. **禁用系统休眠**：`systemctl mask sleep.target`，移动硬盘休眠后 USB 断电无法恢复
7. **安装 NVIDIA 驱动**（见下方 NVIDIA 驱动安装）
8. **安装 Miniconda** → 创建 conda 环境
9. **安装 PyTorch + CUDA**
10. **安装其他软件**（Docker、Fcitx5 等）
11. **安装开发工具**（VS Code、系统依赖等）
12. **安装仿真环境**（MuJoCo）
13. **创建项目工作目录结构**

### 软件安装清单

**系统基础工具**：

```bash
sudo apt update
sudo apt install -y git vim htop tmux tree net-tools iputils-ping curl wget
```

**中文输入法**（记录日志/写文档需要中文输入）：

```bash
sudo apt install -y fcitx5 fcitx5-chinese-addons
```

安装后在 Settings → Language 中添加中文输入源，选择 Fcitx5。

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

安装以上基础的软件包后，进入后续步骤。LeRobot 及其依赖、PyTorch、CUDA 等 Python 包在第 3 章 LeRobot 开发环境中安装。

**开发工具（VS Code）**：

```bash
sudo apt install -y software-properties-common apt-transport-https
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg
sudo install -D -o root -g root -m 644 packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg
sudo sh -c 'echo "deb [arch=amd64,arm64 signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" > /etc/apt/sources.list.d/vscode.list'
rm -f packages.microsoft.gpg
sudo apt update
sudo apt install -y code
```

**仿真环境（MuJoCo 3.6.0）**：

在 LeRobot 的 conda 环境中安装：

```bash
pip install mujoco
# 验证
python -c "import mujoco; print(mujoco.__version__)"
```

LeRobot 内置仿真环境支持 aloha、pusht、unitree_g1 等场景，通过 MuJoCo 渲染。

**ROS2 Humble 安装（尝试但未使用）**：

曾尝试安装 ROS2 Humble 用于机器人开发，但因 SO101 已有 Feetech SDK 直接驱动、LeRobot 框架已满足需求，最终决定暂时搁置。完整安装命令保留供参考：

```bash
# 设置语言环境
sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8

# 添加 ROS2 源
sudo apt install -y curl gnupg lsb-release
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list

# 安装
sudo apt update
sudo apt install -y ros-humble-desktop

# 初始化
source /opt/ros/humble/setup.bash
```

**Isaac SIM 评估**：曾评估安装 NVIDIA Isaac SIM 用于仿真训练，发现需要 Python 3.10/3.11（本项目使用 3.12）且需要 NVIDIA Omniverse 账户，决定不使用，直接用 MuJoCo。

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
nvidia-smi                    # 应显示 RTX 5070
lspci | grep -i nvidia        # 确认 PCIe 设备被识别
```

驱动安装成功后，移除 GRUB 中的 `nomodeset` 参数，恢复正常分辨率。

## CUDA + PyTorch

| 组件 | 版本 |
|------|------|
| CUDA | 13.0 |
| PyTorch | 2.10.0+cu128 |

```bash
python -c "import torch; print(torch.cuda.is_available())"  # 应输出 True
```