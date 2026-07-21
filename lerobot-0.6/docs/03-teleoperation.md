# 03. 遥操作测试

> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)

## 前置条件

- 已完成 [02-calibration.md](02-calibration.md)
- 主臂、从臂均已校准
- 机械臂已上电并连接 USB

## 启动遥操作

```bash
cd /home/j/ws/so101
unset PYTHONPATH
conda activate lerobot

python src/scripts/teleoperate.py \
  --teleop.type=so101_leader \
  --teleop.port=<LEADER_PORT> \
  --teleop.id=j_leader \
  --robot.type=so101_follower \
  --robot.port=<FOLLOWER_PORT> \
  --robot.id=j_follower
```

> 如果你创建了 udev 别名，也可以把 `--port` 替换为 `/dev/ttySO101_LEADER` 和 `/dev/ttySO101_FOLLOWER`。

## 启动后可能出现的校准确认提示

启动后如果看到如下提示：

```text
Mismatch between calibration values in the motor and the calibration file or no calibration file found
Press ENTER to use provided calibration file associated with the id j_leader,
or type 'c' and press ENTER to run calibration:
```

这是正常现象。LeRobot 在对比**电机内部存储的校准值**和**本地校准文件**。因为电机里可能还存着旧值或出厂默认值，所以会询问你用哪个。

- **直接按 ENTER**：使用本地已保存的校准文件（推荐，就是我们刚才校准保存的）。
- **输入 `c` 再按 ENTER**：重新走一遍校准流程。

## `wrist_roll` 固定说明

本项目在 [`src/configs/so101.yaml`](../../src/configs/so101.yaml) 中把从臂的 `wrist_roll`（夹爪旋转关节）固定为 `-27.82°`。

`teleoperate.py` 启动时会自动从 `so101.yaml` 加载 `fixed_joints` 配置，无需手动传参。

这意味着：

- 遥操作时，主臂 `wrist_roll` 的转动**不会**传递给从臂。
- 从臂 `wrist_roll` 始终被强制设为 `-27.82°`。
- 如果你希望测试 `wrist_roll` 的跟随，可以临时注释掉 `src/configs/so101.yaml` 中的 `fixed_joints`。

## 操作与验证

### 基本验证

- [ ] 主臂移动时，从臂能实时跟随移动
- [ ] 除 `wrist_roll` 外，其余 5 个关节都能控制（`wrist_roll` 已固定为 `-27.82°`）
- [ ] 夹爪能完全张开和闭合
- [ ] 按 `Ctrl+C` 能正常退出并释放扭矩

### 安全提示

1. **退出前确保从臂不会坠落**：按 `Ctrl+C` 后程序会调用 `disconnect()`，默认会关闭电机扭矩。确保从臂在退出时处于稳定姿势，避免坠落。
2. **不要用力过猛**：遥操作时用手轻轻带动主臂即可，避免冲击从臂。
3. **注意夹爪开合范围**：夹爪为百分比模式 0-100，测试时避免夹到手指或线缆。

### 常见问题

- **从臂不跟随**：
  - 检查串口是否正确
  - 检查校准文件是否存在且匹配（`~/.cache/huggingface/lerobot/calibration/`）
  - 检查主从臂是否搞反

- **夹爪无力**：
  - 确认已应用 gripper 扭矩 patch：`python apply_patches.py`

- **wrist_roll 范围不对或抖动**：
  - 确认已应用 wrist_roll 校准 patch
  - 重新校准两臂

## 下一步

遥操作正常后，进入 [04-recording.md](04-recording.md) 录制数据。
