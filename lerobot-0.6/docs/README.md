# SO-101 项目操作文档

> 详细记录 SO-101 真机任务的每一步操作。
>
> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)
>
> **基于 LeRobot v0.6.0**，部分 v0.5.x 命令/参数已不兼容，文档中已标注。

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
| - | [07-troubleshooting.md](07-troubleshooting.md) | 常见问题与排查（28 个） |

## 快速开始

```bash
unset PYTHONPATH
conda activate lerobot
cd /home/j/ws/so101
```

## 项目成果

### 最终模型

- **最佳模型**：`so101_smolvla_v1-2`（20k 步，从 v1-1 续训）
- **成功率**：**21/25 = 84%**（25 组测试，每组 30 秒）
- **失败模式**：3 次未抓起 + 1 次夹爪未松开
- **结论**：模型稳定可用，无需 DAgger 迭代纠错

### 完整流程时间线

| 阶段 | 状态 | 关键数据 |
|------|------|---------|
| 1. 硬件连接 | 完成 | 主臂 `ttyACM1`，从臂 `ttyACM0`，2 个摄像头 |
| 2. 机械臂校准 | 完成 | 含 wrist_roll 校准 patch，v0.6.0 适配 |
| 3. 遥操作测试 | 完成 | wrist_roll 锁定 `-27.82°`，自动加载配置 |
| 4. 数据录制 | 完成 | 199 条 episode，52,010 frames，v1-1 ~ v1-20 合并 |
| 5. 模型训练 | 完成 | SmolVLA 分阶段：v1-1 (10k) → v1-2 (20k)，batch=36 |
| 6. 推理部署 | 完成 | 25 组评估，84% 成功率 ✅ |

## 核心决策（新会话必读）

以下决策贯穿整个项目，修改任何配置前先确认：

| 决策 | 内容 | 文档位置 |
|------|------|---------|
| LeRobot 版本 | **v0.6.0**（参考项目 v0.5.1 不兼容） | README.md |
| 任务描述 | `"put grape block in plate"` | 04-recording.md |
| 目标物体 | 仅紫色方块（3.5cm），无干扰物 | 04-recording.md |
| wrist_roll | 固定 `-27.82°`，从 yaml 自动加载 | src/configs/so101.yaml |
| 数据命名 | `v{version}-{group}`（每组 10 条） | 04-recording.md |
| SmolVLA 格式 | 录制 `front`/`top` → 训练 rename → `camera1`/`camera2` | 04/05-training.md |
| 预训练模型 | `checkpoints/smolvla_base_migrated` | 05-training.md |
| 推理必备参数 | `HF_HUB_OFFLINE=1` + `--policy.empty_cameras=1` + `--rename_map` | 06-inference.md |
| 评估方式 | 25 组 × 30 秒，episodic 策略自动运行 | 06-inference.md |

## 关键坑点速查

1. **PYTHONPATH 污染**：切换 conda 后必须 `unset PYTHONPATH`
2. **fixed_joints 不生效**：已改为从 yaml 自动加载，不要 CLI 手动传
3. **录制必须 `--teleop.*`**：否则复位阶段从臂不跟随
4. **v0.6.0 时间戳**：`repo_id` 自动追加时间戳，训练用实际名字或 `--dataset.root`
5. **SmolVLA 相机键名**：必须是 `camera1`/`camera2`，录制 `front`/`top` 需 rename_map
6. **代理/镜像**：GitHub 慢用 `127.0.0.1:7897` 或 `ghfast.top`
7. **`--output_dir` 已移除**：v0.6.0 改用 `--dataset.root` 和 `--policy.path`
8. **`episodic` 策略参数**：用 `--dataset.*` 前缀，数据集名以 `rollout_` 开头
9. **视频编码参数**：`--dataset.vcodec` → `--dataset.rgb_encoder.vcodec`
10. **训练视频后端**：`--dataset.video_backend=pyav` 避免 torchcodec 加载失败
11. **`--steps` 是总步数**：恢复训练时指定总步数，不是额外步数
12. **数据集合并**：v0.6.0 禁用 MultiLeRobotDataset，需先 `lerobot-edit-dataset` 物理合并

## 注意事项

- 所有操作前确保机械臂已正确上电并连接 USB
- 串口名称可能为 `/dev/ttyUSB0`、`/dev/ttyACM0` 等，以实际为准
- 操作前建议备份校准文件和数据集
- 本项目基于 **LeRobot v0.6.0**，部分参考项目（v0.5.1）的命令/参数已不兼容，文档中已标注
- 详细 AI 接手指南见根目录 [README.md](../README.md) 的"AI 新会话接手指南"章节