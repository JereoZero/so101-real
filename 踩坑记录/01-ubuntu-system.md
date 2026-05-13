# 1. Ubuntu 系统环境搭建

## 1.1 移动硬盘启动黑屏

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