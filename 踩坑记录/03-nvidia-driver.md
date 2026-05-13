# 3. NVIDIA 驱动与 CUDA

## 3.1 老主板 + RTX 5070：BIOS 更新排查全过程

这是整个项目中最耗时、最隐蔽的一个坑。以下按时间线还原真实排查过程。

### 阶段一：真机首次启动 — 只能进命令行

移动固态硬盘从虚拟机搬到台式机（B450M + RTX 5070）上首次启动：

- **现象**：系统只能进入 tty 命令行模式，桌面 GUI 无法启动
- **原因**：没有安装 NVIDIA 驱动，nouveau 开源驱动无法正常驱动 RTX 5070
- **应对**：好在虚拟机阶段已经配置好了 SSH，通过网络从另一台电脑 SSH 远程登录，在命令行下安装 NVIDIA 驱动

### 阶段二：安装驱动后 — GUI 亮了，但不稳定

按照驱动安装流程（见 3.2），装了 `nvidia-driver-580-open` 之后重启：

- GUI 桌面可以正常进入了
- `nvidia-smi` 能识别到 RTX 5070
- 但系统并不稳定：偶尔开机黑屏、显卡识别异常、性能表现不正常
- **这一阶段花了大量时间排查**：反复重装驱动、检查 dkms、检查内核版本、检查 GCC 兼容性……都不见效

### 阶段三：发现真相 — BIOS 是根因

经过长时间排查（期间尝试了各种驱动版本、内核参数、GRUB 配置），最终怀疑到主板 BIOS 上：

- **确认主板型号**：B450M（属于老平台）
- **检查 BIOS 版本**：发现 BIOS 固件版本太老，连 Resizable BAR / Above 4G Decoding 的支持都不完善
- **根因**：RTX 5070 是 Blackwell 新架构，B450M 老主板的默认 BIOS 固件存在以下问题：
  1. **UEFI GOP 驱动过旧**：主板内置的 Graphics Output Protocol 驱动不识别 RTX 5070，导致开机时显卡初始化失败
  2. **PCIe 初始化不兼容**：老 BIOS 对 PCIe Gen4/Gen5 的初始化流程与新显卡有差异
  3. **Resizable BAR 支持有 bug**：老版本 BIOS 的 Resizable BAR 实现与 Blackwell 架构冲突

### 解决方案

1. 到主板厂商官网，下载 B450M 对应的最新 BIOS 固件
2. 通过内置更新工具（EZ Flash / M-Flash / Q-Flash）刷入
3. 更新完成后恢复默认设置，重新配置：
   - 开启 **Resizable BAR**（或 Above 4G Decoding）
   - 关闭 **SecureBoot**
   - 关闭 **CSM**（Compatibility Support Module），使用纯 UEFI 启动
4. 保存并重启

更新 BIOS 后，所有之前的不稳定问题全部消失。

### 核心教训

> **新显卡 + 老主板，BIOS 更新不是"可选项"而是"必选项"**。而且这个坑的隐蔽之处在于：驱动安装之后 GUI 能亮、nvidia-smi 能识别，很容易让人觉得"驱动装好了就完事了"，实际上底层硬件初始化层面的问题（BIOS）会持续导致不稳定。这是整个项目遇到的第一个硬件级别的坑，排查周期最长。

---

## 3.2 驱动安装

直接安装最新 open 版驱动即可，不需要折腾旧版本：

```bash
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update
sudo apt install -y nvidia-driver-580-open
sudo reboot
```

> **注意**：`nvidia-driver-580` 和 `nvidia-driver-580-open` 是两个不同的包！RTX 5070（Blackwell 架构）强制要求使用 open kernel module，专有版驱动不支持。如果之前装过专有版，需要先彻底卸载：`sudo apt-get remove --purge nvidia-driver-580 nvidia-dkms-580 -y`

安装完成后验证：

```bash
nvidia-smi
```

本项目实际使用的驱动及版本：

```text
$ nvidia-smi
Driver Version: 580.126.20     CUDA Version: 13.0
GPU: NVIDIA GeForce RTX 5070 (12GB)
```

---

## 3.3 GCC 版本导致驱动编译失败

如果 DKMS 编译报错，可能是 GCC 版本不兼容：

```bash
sudo apt install gcc-12
# 编译时 CC=/usr/bin/gcc-12
```

---

## 3.4 最终版本组合

| 组件 | 版本 |
|------|------|
| NVIDIA 驱动 | 580.126.20 (open) |
| CUDA | 13.0 |
| PyTorch | 2.10.0+cu128 |

验证命令：

```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```