# SO101 机器人学习项目 - 完整流程记录

> 本项目从零搭建机器人学习系统，基于 LeRobot + SmolVLA，使用 SO101 双臂机械臂完成"将小方块放入盘子"的任务。

## 文档结构

| 章节 | 文件 | 内容 |
|------|------|------|
| 1 | [01-task-overview.md](./01-task-overview.md) | 任务描述，物理环境，难点，整体架构，工作模式 |
| 2 | [02-hardware-setup.md](./02-hardware-setup.md) | 硬件配置，Ubuntu 便携系统，BIOS 更新，NVIDIA 驱动，CUDA |
| 3 | [03-dev-environment.md](./03-dev-environment.md) | LeRobot 环境安装，SO101 配置与校准，4处源码修改，摄像头 |
| 4 | [04-planning.md](./04-planning.md) | 算法选型(SmolVLA)，场景分级(L1-L3)，指令设计，数据量规划，光照策略 |
| 5 | [05-data-collection.md](./05-data-collection.md) | 录制命令与键位，迭代过程(v1→v6)，9组baseline+增强，回放验证，数据集整理 |
| 6 | [06-model-training.md](./06-model-training.md) | 预训练模型准备，训练命令，三轮训练(10000→40000→40000 V3)，batch_size 变化(8→36) |
| 7 | [07-model-inference.md](./07-model-inference.md) | 模型导出，推理命令，V1/V2 vs V3 版本对比，颜色切换，eval_前缀 |
| 8 | [08-summary.md](./08-summary.md) | 技术栈版本一览，全流程概览，核心数据，关键经验 |

## 快速导航

- 遇到了问题 → [../踩坑记录/](../踩坑记录/)
- 项目代码与原始文档 → `../docs/`（同机器内的原始文档目录）