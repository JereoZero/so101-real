# SO101 机器人学习项目 - 踩坑全记录

> 本项目基于 LeRobot 框架 + SmolVLA 算法，使用 SO101 双臂机械臂完成"将小方块放入盘子"的任务。
> 硬件：NVIDIA RTX 5070 12GB，AMD Ryzen 7 3700X，96GB DDR4，Ubuntu 22.04 移动固态硬盘。

## 文档结构

| 章节 | 文件 | 内容 |
|------|------|------|
| 1 | [01-ubuntu-system.md](./01-ubuntu-system.md) | Ubuntu 系统环境搭建（黑屏、分辨率、自动更新、休眠、SSH等） |
| 2 | [02-network.md](./02-network.md) | 网络相关问题（GitHub 慢、GnuTLS、HuggingFace 被墙） |
| 3 | [03-nvidia-driver.md](./03-nvidia-driver.md) | NVIDIA 驱动与 CUDA（BIOS更新、open版驱动、Resizable BAR等） |
| 4 | [04-lerobot-env.md](./04-lerobot-env.md) | LeRobot 环境安装（Python、依赖、SDK冲突） |
| 5 | [05-so101-hardware.md](./05-so101-hardware.md) | SO101 机械臂硬件（电机ID、夹爪扭矩、串口、udev、红灯） |
| 6 | [06-camera.md](./06-camera.md) | 摄像头配置（fourcc、占用、by-id vs index、GUI依赖） |
| 7 | [07-source-modifications.md](./07-source-modifications.md) | LeRobot 源码修改（wrist_roll、夹爪、容错、teleop修复） |
| 8 | [08-data-recording.md](./08-data-recording.md) | 数据录制（teleop参数、键位、难点、光照控制、fixed_joints） |
| 9 | [09-model-training.md](./09-model-training.md) | 模型训练（预训练模型、rename_map、Resume Bug、离线配置） |
| 10 | [10-model-inference.md](./10-model-inference.md) | 模型推理（路径问题、eval_前缀、Feature匹配） |
| 附录 | [11-appendix.md](./11-appendix.md) | 诊断命令、关键路径、项目参数配置 |

## 项目流程

完整时间线和流程记录见 [workflow.md](./workflow.md)。