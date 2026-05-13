# 01 — Ubuntu 22.04 系统安装与避坑

## 1.0 Ubuntu 系统安装到移动固态硬盘的制作流程

### 为什么选移动硬盘

项目全程在移动固态硬盘（USB 3.0 外接）上运行，包括系统、代码、数据集和模型。主要原因：
- 在不同电脑间切换（家里台式机、调试用笔记本等），各自有各自的硬件环境
- 不怕主机系统崩溃，数据和系统独立
- 完整的 GPU 驱动能力不受影响（只要有 NVIDIA 显卡即可）

### 安装方案选择：从 U 盘到虚拟机

最初尝试用 U 盘启动盘直接在实机上安装 Ubuntu，但遇到了两个致命问题：

1. **显卡不兼容导致无法开机**：RTX 5070（Blackwell 架构）插在 B450M 老主板上，U 盘启动后无法正常进入安装界面，或者安装完成后系统无法启动
2. **磁盘选择容易出错**：Ubuntu 安装界面会列出所有硬盘（包括 Windows 系统盘和启动 U 盘本身），容易误操作导致 Windows 系统被覆盖

因此最终采用的方案是：**在虚拟机中先把系统安装到移动固态硬盘**。

### 虚拟机安装流程

1. 在 Windows 上安装虚拟机软件（如 VMware Workstation 或 VirtualBox）
2. 将移动固态硬盘连接到虚拟机，挂载为虚拟机的物理磁盘
3. 在虚拟机中用 Ubuntu 22.04 ISO 启动，安装到该移动固态硬盘
4. 安装完成后，在虚拟机中完成以下配置（这些不需要实机环境）：
   - 替换 apt 源（阿里云镜像）
   - 安装 OpenCode 终端版
   - 用 OpenCode 安装基础工具（git, vim, htop, tmux, curl, wget 等）
   - **安装并配置 SSH server（这是关键——后面真机首次启动只有命令行，全靠 SSH 远程操作）**
   - 安装 Miniconda、配置 conda 环境
   - 配置 GRUB（添加 nomodeset 参数，防止首次实机启动黑屏）
   - 禁用自动更新和系统休眠
5. 虚拟机中能装的都装好之后，关机，拔出移动固态硬盘，插到目标台式机上
6. 通过 BIOS 启动菜单选择从移动固态硬盘启动

### 虚拟机→真机：首次启动全过程

这是整个项目中最关键也最折腾的一步。移动固态硬盘从虚拟机搬到真实硬件上，并不会直接点亮桌面：

**实际情况**：
1. 从移动固态硬盘启动后，只能进入 **tty 命令行模式**，桌面 GUI 无法启动（因为没有 NVIDIA 驱动）
2. 但好在虚拟机阶段已经配置好了 SSH server，此时通过网络用另一台电脑 SSH 远程登录
3. 在 SSH 远程命令行下，安装 NVIDIA 驱动（`nvidia-driver-580-open`）
4. 驱动安装完成后重启，桌面 GUI 才能正常亮起
5. **但是**——GUI 亮起来之后环境仍然有问题，排查了很长时间（显卡识别不稳定、性能异常等），最终才发现是 **BIOS 版本过旧**导致的，需要更新 BIOS 固件（详见 [03-nvidia-driver.md](./03-nvidia-driver.md)）

> **核心教训**：对于移动硬盘系统 + 新显卡 + 老主板的组合，虚拟机安装是可靠的方式，但必须提前配置好 SSH，因为真机首次启动大概率只有命令行。后续的 BIOS 问题是另一个坑——即使驱动装好了，老 BIOS 仍然会导致各种不稳定。

### 安装后系统标识

```bash
$ whoami
jer
$ hostname
smolvlabuntu
$ pwd
/home/jer
```

---

## 1.1 移动硬盘启动黑屏（nomodeset）

**现象**：Ubuntu 22.04 安装在移动固态硬盘上，插到某些电脑上直接黑屏，无法进入系统。

**原因**：不同电脑的显卡差异大，nouveau 开源驱动可能无法正常初始化某些 NVIDIA 显卡。

**解决**：在 GRUB 中添加 `nomodeset` 参数，禁止内核加载显卡驱动：

```bash
sudo nano /etc/default/grub
# 修改：GRUB_CMDLINE_LINUX="nomodeset"
sudo update-grub
```

**代价**：nomodeset 会导致分辨率固定且无法调节（见 1.2），因此只是一个临时方案。

---

## 1.2 分辨率无法调节

**现象**：使用 nomodeset 后屏幕能亮但分辨率锁死，无法在系统设置中调节。

**原因**：nomodeset 阻止了内核模式设置（KMS），NVIDIA 驱动无法接管显示，只能使用基础的 VESA 驱动，分辨率受限。

**三种解决方案**：

**方案1（推荐）：安装 NVIDIA 驱动后移除 nomodeset**

```bash
# 1. 在 nomodeset 模式下进入系统，安装 NVIDIA 驱动
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update
sudo apt install nvidia-driver-580-open

# 2. 重启时在 GRUB 菜单按 e，临时移除 nomodeset 试试
# 如果能正常进入且分辨率正常，再永久移除

# 3. 永久移除 nomodeset
sudo nano /etc/default/grub
# 将 GRUB_CMDLINE_LINUX="nomodeset" 改为 GRUB_CMDLINE_LINUX=""
sudo update-grub
```

**方案2：保持 nomodeset，用 xrandr 强制设置分辨率**

```bash
# 查看当前显示器和可用分辨率
xrandr

# 强制设置分辨率（以 1920x1080 为例）
xrandr --output <显示器名称> --mode 1920x1080

# 持久化设置（添加到 ~/.profile）
```

**方案3：针对特定电脑单独配置**

只在某几台电脑使用时，可以针对这些电脑单独配置启动参数（通过 GRUB 菜单手动选择），不修改全局配置。

| 启动参数 | 优点 | 缺点 |
|----------|------|------|
| 无 nomodeset | 驱动正常工作，高分辨率 | 可能黑屏进不去系统 |
| 有 nomodeset | 一定能亮屏 | 分辨率受限 |

---

## 1.3 移动硬盘在不同电脑上启动失败

**现象**：在某些电脑上无法从移动硬盘启动系统。

**可能原因与排查**：
1. **BIOS/UEFI 设置问题**：确认 BIOS 中设置了从 USB 启动，且启动顺序正确
2. **USB 供电不足**：尝试使用主板背面的 USB 3.0 接口（非前置面板），避开 USB Hub
3. **显卡不兼容**：参考 1.1 使用 nomodeset 启动参数
4. **关闭 SecureBoot 并确保 CSM/UEFI 模式匹配原来安装时的设置**

---

## 1.4 系统自动更新导致移动硬盘读写崩溃

**现象**：移动硬盘运行时系统自动更新，后台大量读写导致系统卡死或报错。

**原因**：移动硬盘的 IO 性能有限，apt 后台更新占用大量 IO，与开发任务争抢资源。

**解决**：彻底禁用自动更新：

```bash
sudo systemctl disable apt-daily.timer
sudo systemctl disable apt-daily-upgrade.timer
sudo systemctl stop apt-daily.service
sudo systemctl stop apt-daily-upgrade.service
```

---

## 1.5 休眠后无法唤醒

**现象**：系统进入休眠/挂起状态后无法唤醒，只能强制重启。

**原因**：移动硬盘系统在休眠时 USB 断电，恢复时无法重新挂载根文件系统。

**解决**：彻底禁用休眠和挂起：

```bash
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

---

## 1.6 文件系统错误

**现象**：强关后启动时提示文件系统错误。

**解决**：

```bash
sudo touch /forcefsck
sudo reboot  # 重启会自动 fsck
```

---

## 1.7 网卡未启用

**现象**：ens33 网卡没有 IP 地址或显示 DOWN，无法上网。

**解决**：

```bash
# 启用网卡
sudo ip link set ens33 up

# 获取 IP（DHCP）
sudo dhclient ens33

# 验证
ip a show ens33
ping -c 4 8.8.8.8
```

---

## 1.8 SSH 连接不上

**现象**：想远程操作但 SSH 连不上。

**排查步骤**：

```bash
# 1. 检查 SSH 服务状态
sudo systemctl status ssh

# 2. 检查 SSH 进程是否运行
ps aux | grep sshd

# 3. 检查端口监听
sudo netstat -tuln | grep 22

# 4. 检查防火墙
sudo ufw status
sudo ufw allow ssh
```

**解决**：

```bash
# 安装并启动 SSH
sudo apt install -y openssh-server
sudo systemctl start ssh
sudo systemctl enable ssh
```

---

## 1.9 阿里云镜像源配置

**背景**：默认 Ubuntu 官方源在国内速度极慢，必须替换为国内镜像。

```bash
sudo sed -i 's/archive.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
sudo sed -i 's/security.ubuntu.com/mirrors.aliyun.com/g' /etc/apt/sources.list
sudo apt update
```

---

## 1.10 add-apt-repository 命令不存在

**现象**：执行 `add-apt-repository` 时报 `command not found`。

**解决**：

```bash
sudo apt install -y software-properties-common
```

---

## 1.11 apt 安装依赖修复

**现象**：apt install 时出现依赖错误，安装中断。

**解决**：

```bash
# 修复损坏的依赖关系
sudo apt --fix-broken install -y

# 更新软件源后重试
sudo apt update
sudo apt upgrade -y

# 清理缓存
sudo apt clean
sudo apt autoclean
```

---

## 1.12 基础工具安装

新系统必须首先安装的开发必备工具：

```bash
sudo apt install -y git vim htop tmux tree net-tools iputils-ping curl wget
```

---

## 1.13 系统诊断命令

排查系统问题时常用的命令：

```bash
# 查看系统日志（排查驱动/硬件/启动问题）
dmesg | tail
journalctl -xe
sudo tail -f /var/log/syslog
sudo tail -f /var/log/kern.log

# 硬件检测
lspci | grep -i vga         # 查看显卡
lspci | grep -i nvidia      # 确认 NVIDIA 显卡被识别
lsusb                       # USB 设备列表
free -h                     # 内存使用
df -h                       # 磁盘空间

# 网络诊断
ping -c 4 8.8.8.8           # 测试能否上网
cat /etc/resolv.conf         # 查看 DNS 配置
ip a                         # 查看网络接口
```