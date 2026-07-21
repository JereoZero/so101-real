# SO-101 项目操作文档

> 详细记录 SO-101 真机任务的每一步操作。
>
> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)

## 设备 ID 占位符说明

本文档中的命令使用以下占位符代替实际设备路径。**这些 ID 是本机特有的，不会上传到 GitHub**。

| 占位符 | 含义 | 查看方式 |
|--------|------|---------|
| `<FOLLOWER_PORT>` | 从臂串口 | `ls /dev/serial/by-id/` |
| `<LEADER_PORT>` | 主臂串口 | `ls /dev/serial/by-id/` |
| `<FRONT_CAM>` | 爪子视角摄像头 | `ls /dev/v4l/by-id/` |
| `<TOP_CAM>` | 顶部视角摄像头 | `ls /dev/v4l/by-id/` |

实际值见本地文件 `src/configs/so101.yaml`（已被 gitignore，不上传）。

## 文档索引

| 步骤 | 文档 | 内容 |
|------|------|------|
| 1 | [01-hardware-setup.md](01-hardware-setup.md) | 硬件连接、串口确认、上电检查 |
| 2 | [02-calibration.md](02-calibration.md) | 机械臂校准流程 |
| 3 | [03-teleoperation.md](03-teleoperation.md) | 遥操作测试 |
| 4 | [04-recording.md](04-recording.md) | 数据录制 |
| 5 | [05-training.md](05-training.md) | 模型训练 |
| 6 | [06-inference.md](06-inference.md) | 推理部署 |
| - | [07-troubleshooting.md](07-troubleshooting.md) | 常见问题与排查 |

## 快速开始

```bash
unset PYTHONPATH
conda activate lerobot
cd /home/j/ws/so101
```

## 进度状态

| 步骤 | 状态 | 说明 |
|------|------|------|
| 1. 硬件连接 | 完成 | 设备 ID 已记录，串口稳定 |
| 2. 机械臂校准 | 完成 | 含 wrist_roll 校准 patch |
| 3. 遥操作测试 | 完成 | wrist_roll 已锁定 `-27.82°`，自动加载配置 |
| 4. 数据录制 | 进行中 | 设计完成，准备录 v0-1 |
| 5. 模型训练 | 待开始 | |
| 6. 推理部署 | 待开始 | |

## 核心决策（新会话必读）

以下决策贯穿整个项目，修改任何配置前先确认：

| 决策 | 内容 | 文档位置 |
|------|------|---------|
| LeRobot 版本 | **v0.6.0**（参考项目 v0.5.1 不兼容） | README.md AI 接手指南 |
| 任务描述 | `"put grape block in plate"` | 04-recording.md |
| 目标物体 | 仅紫色方块（3.5cm），无干扰物 | 04-recording.md |
| wrist_roll | 固定 `-27.82°`，从 yaml 自动加载 | src/configs/so101.yaml |
| 数据命名 | `v{version}-{group}`（每组 10 条） | 04-recording.md |
| SmolVLA 格式 | 录制 `front`/`top` → 训练 rename → `camera1`/`camera2` | 04/05-training.md |
| 预训练模型 | `checkpoints/smolvla_base_migrated` | 05-training.md |

## 关键坑点速查

1. **PYTHONPATH 污染**：切换 conda 后必须 `unset PYTHONPATH`
2. **fixed_joints 不生效**：已改为从 yaml 自动加载，不要 CLI 手动传
3. **录制必须 `--teleop.*`**：否则复位阶段从臂不跟随
4. **v0.6.0 时间戳**：`repo_id` 自动追加时间戳，训练用实际名字或 `--dataset.root`
5. **SmolVLA 相机键名**：必须是 `camera1`/`camera2`，录制 `front`/`top` 需 rename_map
6. **代理/镜像**：GitHub 慢用 `本机 HTTP 代理` 或 `ghfast.top`

## 注意事项

- 所有操作前确保机械臂已正确上电并连接 USB
- 串口名称可能为 `/dev/ttyUSB0`、`/dev/ttyACM0` 等，以实际为准
- 操作前建议备份校准文件和数据集
- 本项目基于 **LeRobot v0.6.0**，部分参考项目（v0.5.1）的命令/参数已不兼容，文档中已标注
- 详细 AI 接手指南见根目录 [README.md](../README.md) 的"AI 新会话接手指南"章节