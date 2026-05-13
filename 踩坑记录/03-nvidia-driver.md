# 3. NVIDIA 驱动与 CUDA

## 3.1 老主板 + RTX 5070：必须更新 BIOS 固件

**现象**：显卡 RTX 5070 插在老主板上（如 X570/B450 等旧平台），开机黑屏或显卡完全不识别，连 BIOS 界面都进不去，或者进了系统后显卡始终无法被识别。

**原因**：RTX 5070 是 Blackwell 架构，老主板的 BIOS/UEFI 固件没有针对新显卡的兼容性支持。具体表现为：

1. **UEFI GOP 驱动过旧**：主板内置的 Graphics Output Protocol 驱动不识别 RTX 5070，导致开机无显示
2. **PCIe 初始化不兼容**：老 BIOS 对 PCIe Gen4/Gen5 的初始化流程与新显卡有差异
3. **Resizable BAR 支持不完善**：老版本 BIOS 的 Resizable BAR 实现有 bug，与 Blackwell 架构冲突

**解决**：

1. **确认主板型号并下载最新 BIOS**：到主板厂商官网（华硕/微星/技嘉等）查找对应型号的最新 BIOS
2. **更新 BIOS**：
   - 准备一个 FAT32 格式的 U 盘
   - 将下载的 BIOS 文件放入 U 盘根目录
   - 重启进入 BIOS → 使用内置的 EZ Flash / M-Flash / Q-Flash 工具更新
   - 更新完成后恢复默认设置再重新配置
3. **更新完 BIOS 后需要重新配置以下选项**：
   - 开启 **Resizable BAR**（或 Above 4G Decoding）
   - 关闭 **SecureBoot**
   - 部分主板还需关闭 **CSM**（Compatibility Support Module），强制使用纯 UEFI 启动

> **踩坑教训**：新显卡配老主板，BIOS 更新不是"可选项"而是"必选项"。不更新的话，即使后面驱动安装正确，显卡也可能完全不被识别。这是整个项目遇到的第一个硬件级别的坑——因为装好显卡后开机黑屏，连排查的机会都没有。

---

## 3.2 驱动安装试错全过程

RTX 5070 的驱动安装并非一蹴而就，经历了多次失败才找到正确的安装方式：

| 尝试 | 驱动版本 | 结果 | 原因 |
|------|----------|------|------|
| 第1次 | nvidia-driver-550 | ❌ 安装失败 | 版本太低，不支持 RTX 5070（Blackwell 需要 ≥ 570） |
| 第2次 | nvidia-driver-570 | ❌ 编译失败 | DKMS 编译时 GCC 版本不兼容 |
| 第3次 | nvidia-driver-580 | ❌ nvidia-smi 显示 "No devices were found" | 专有版驱动不支持 Blackwell，必须用 open 版 |
| 第4次 | nvidia-driver-580-open | ✅ 成功 | 开放内核模块版本 |

### 第1次失败：版本过低

RTX 5070 是 Blackwell 架构，最低驱动要求比预期更高。`nvidia-driver-550` 直接安装失败，提示不支持该 GPU。

### 第2次失败：GCC 编译不兼容

`nvidia-driver-570` 在 DKMS 编译内核模块时报错。Ubuntu 22.04 默认的 GCC 版本与 NVIDIA 驱动不完全兼容。解决方式是安装 `gcc-12` 并在编译时指定：

```bash
sudo apt install gcc-12
# 编译时 CC=/usr/bin/gcc-12
```

但即使 GCC 兼容，570 对 Blackwell 的支持仍不完善。

### 第3次失败：专有驱动 vs Open 驱动

安装了 `nvidia-driver-580` 后，`nvidia-smi` 仍然报：
```
NVRM: The NVIDIA GPU installed in this system requires use of the NVIDIA open kernel modules.
```

这是最关键的一步——**RTX 5070 强制要求使用 open kernel module，专有版驱动完全不支持**。`nvidia-driver-580` 和 `nvidia-driver-580-open` 是两个不同的包！

### 第4次：终于成功

```bash
# 先彻底卸载之前残留的驱动和 dkms 模块
sudo apt-get remove --purge nvidia-driver-580 nvidia-dkms-580 -y

# 安装 open 版本
sudo apt-get install -y nvidia-driver-580-open

sudo reboot
```

**关键教训**：如果之前装过专有版驱动，必须连同 `nvidia-dkms-580` 一起彻底卸载，否则残留的 DKMS 模块会干扰新驱动的编译。最终验证通过 —— 驱动 580.126.20，CUDA 13.0，PyTorch 正常识别 GPU。

---

## 3.3 RTX 5070 驱动选择要点：open 版本

**现象**：安装 `nvidia-driver-580` 后，`nvidia-smi` 报 `No devices were found`，内核日志显示：
```
NVRM: The NVIDIA GPU installed in this system requires use of the NVIDIA open kernel modules.
```

**原因**：RTX 5070 属于 Blackwell 架构（PCI ID: 10de:2f04），NVIDIA 从 Blackwell 开始强制要求使用开放内核模块（open kernel module），不再支持传统的专有内核模块。

**解决**：

```bash
# 先添加 NVIDIA 驱动 PPA 源
sudo add-apt-repository ppa:graphics-drivers/ppa
sudo apt update

# 卸载专有驱动（含 dkms）
sudo apt-get remove --purge nvidia-driver-580 nvidia-dkms-580 -y

# 安装开放内核模块版本（注意包名后缀 -open）
# RTX 5070 需要 >= 550 版本驱动
sudo apt-get install -y nvidia-driver-580-open

sudo reboot
```

**踩坑经验**：`nvidia-driver-580` 和 `nvidia-driver-580-open` 是两个不同的包！后者才有 open kernel module。而且 open 版驱动对 BIOS/UEFI 固件版本有较高要求，所以必须先更新 BIOS（见 3.1），否则 open 驱动也无法加载。**如果之前装过专有版驱动，必须连同 `nvidia-dkms-580` 一起彻底卸载**，否则残留的 DKMS 模块会干扰新驱动的编译。

---

## 3.4 BIOS 必须开启 Resizable BAR + 关闭 SecureBoot

**现象**：即使安装了正确的 open 驱动，驱动仍然无法加载。

**原因**：NVIDIA open kernel module 依赖 BIOS 中的 Resizable BAR（或 Above 4G Decoding）功能，且 SecureBoot 会阻止未签名的内核模块加载。

**解决**：进入 BIOS 设置：
- **开启** Resizable BAR（或 Above 4G Decoding）
- **关闭** SecureBoot

---

## 3.5 GCC 版本导致驱动编译失败

**现象**：安装 NVIDIA 驱动时 DKMS 编译失败，日志显示 GCC 版本不兼容。

**原因**：Ubuntu 22.04 默认 GCC 版本可能与 NVIDIA 570/580 驱动不完全兼容。

**解决**：安装特定版本的 GCC 并在编译时指定：

```bash
sudo apt install gcc-12
# 在编译时 CC=/usr/bin/gcc-12
```

---

## 3.6 驱动版本与 CUDA 版本的对应关系

**关键经验**：必须确保驱动版本 >= CUDA 工具包要求的最低版本。

本项目最终使用的版本组合：

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