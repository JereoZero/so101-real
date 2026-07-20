# SO-101 项目操作文档

> 详细记录 SO-101 真机任务的每一步操作。
>
> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)

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

## 注意事项

- 所有操作前确保机械臂已正确上电并连接 USB
- 串口名称可能为 `/dev/ttyUSB0`、`/dev/ttyACM0` 等，以实际为准
- 操作前建议备份校准文件和数据集
- 本项目基于 **LeRobot v0.6.0**，部分参考项目（v0.5.1）的命令/参数已不兼容，文档中已标注