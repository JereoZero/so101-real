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

### 安装流程

1. **制作 Ubuntu 22.04 启动盘**，安装到移动固态硬盘
2. **配置 GRUB**：添加 `nomodeset` 参数防止不兼容显卡黑屏
3. **替换镜像源**：官方源 → 阿里云镜像，加速国内下载
4. **安装软件**：按顺序安装以下软件包
5. **禁用自动更新**：`systemctl disable apt-daily`，避免后台 IO 抢占
6. **禁用系统休眠**：`systemctl mask sleep.target`，移动硬盘休眠后 USB 断电无法恢复
7. **配置 SSH**：安装 openssh-server，开机自启，远程操作

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