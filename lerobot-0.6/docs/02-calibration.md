# 02. 机械臂校准

> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)  
> 参考项目文档：[03-dev-environment.md](https://github.com/JereoZero/so101-real/blob/main/%E9%A1%B9%E7%9B%AE%E6%B5%81%E7%A8%8B/03-dev-environment.md)

## 前置条件

- 已完成 [01-hardware-setup.md](01-hardware-setup.md)
- 已确认主臂 / 从臂串口对应关系
- 已应用 SO-101 patch（包括 `wrist_roll` 校准、夹爪扭矩、录制复位修复、电机通信容错）

```bash
unset PYTHONPATH
conda activate lerobot
cd /home/j/ws/so101
python apply_patches.py
```

## SO-101 关节配置

每条机械臂有 6 个 Feetech STS3215 舵机：

| ID | 名称 | 功能 | 模式 |
|----|------|------|------|
| 1 | shoulder_pan | 肩膀水平旋转 | 角度模式 |
| 2 | shoulder_lift | 肩膀升降 | 角度模式 |
| 3 | elbow_flex | 肘部弯曲 | 角度模式 |
| 4 | wrist_flex | 腕部弯曲 | 角度模式 |
| 5 | wrist_roll | 腕部旋转（360°） | 角度模式 |
| 6 | gripper | 夹爪 | 百分比模式（0-100） |

## 校准原则

**每次断电重新连接后都必须重新校准。**

校准的目的是让 LeRobot 知道每个关节的实际运动范围（range min / max）和 homing offset。只有校准完成后，从臂才能正确跟随主臂，录制和回放才不会出错。

> SO-101 patch 会把 `wrist_roll`（第 5 关节）也加入校准，而不是像原版那样固定写死 0-4095。因此校准时需要把 `wrist_roll` 也完整走过一次范围。
>
> 同时 patch 做了两处 v0.6.0 适配：
> - 把传入 `record_ranges_of_motion` 的参数从 `self.bus.motors`（dict）改成了 `list(self.bus.motors.keys())`，避免 `TypeError`。
> - `wrist_roll` 是 360° 旋转关节，校准后可能出现负值（越界回绕），patch 会把它裁剪到 `[0, 4095]` 范围内再写入电机。
>
> 如果校准时报 `TypeError: {'shoulder_pan': Motor(...), ...}` 或 `ValueError: Negative values are not allowed`，先执行 `python apply_patches.py` 更新 patch。

## 校准命令

使用 `lerobot-calibrate` 分别校准主臂和从臂：

```bash
unset PYTHONPATH
conda activate lerobot

# 1. 校准主臂（Leader / Teleoperator）
lerobot-calibrate \
  --teleop.type=so101_leader \
  --teleop.port=<LEADER_PORT> \
  --teleop.id=j_leader

# 2. 校准从臂（Follower / Robot）
lerobot-calibrate \
  --robot.type=so101_follower \
  --robot.port=<FOLLOWER_PORT> \
  --robot.id=j_follower
```

> 如果你创建了 udev 别名 `/dev/ttySO101_LEADER` 和 `/dev/ttySO101_FOLLOWER`，也可以直接替换上面的 `--port`。

## 校准操作步骤

以从臂为例，主臂操作相同。

### 第一步：移动到中位

程序会提示：

```text
Move SOFollower to the middle of its range of motion and press ENTER....
```

**操作**：用手轻轻把从臂移动到各关节的中间位置（不要用力掰，不要到极限位置），然后按 ENTER。

这一步用于设置 `homing_offset`。

### 第二步：遍历整个运动范围

程序会提示：

```text
Move all joints sequentially through their entire ranges of motion.
Recording positions. Press ENTER to stop...
```

**操作**：

1. 保持关节扭矩关闭（此时可以手动活动机械臂）。
2. 依次把每个关节缓慢移动到最小位置和最大位置，让程序记录范围。
3. 建议每个关节至少走一次完整行程（最小 → 最大 → 中间）。
4. 全部完成后按 ENTER。

> **注意**：由于已应用 `wrist_roll` 参与校准的 patch，第 5 关节 `wrist_roll` 也需要完整走过其范围，不要跳过。

### 第三步：保存校准文件

程序会自动保存校准文件并退出，例如：

```text
Calibration saved to /home/j/.cache/huggingface/lerobot/calibration/robots/so_follower/j_follower.json
```

## 校准文件位置

| 设备 | 实际保存路径 |
|------|-------------|
| 主臂 | `~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/j_leader.json` |
| 从臂 | `~/.cache/huggingface/lerobot/calibration/robots/so_follower/j_follower.json` |

> 参考项目文档里写的是 `teleoperators/so101_leader/...`，但 LeRobot v0.6.0 的 teleoperator name 是 `so_leader`，所以实际路径是 `so_leader`。

### 备份与恢复

建议校准成功后备份校准文件，换系统或重装环境时可以直接恢复：

```bash
# 备份
mkdir -p /home/j/ws/so101/checkpoints/calibration
cp ~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/j_leader.json \
   /home/j/ws/so101/checkpoints/calibration/
cp ~/.cache/huggingface/lerobot/calibration/robots/so_follower/j_follower.json \
   /home/j/ws/so101/checkpoints/calibration/

# 恢复（如需）
mkdir -p ~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader
mkdir -p ~/.cache/huggingface/lerobot/calibration/robots/so_follower
cp /home/j/ws/so101/checkpoints/calibration/j_leader.json \
   ~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/
cp /home/j/ws/so101/checkpoints/calibration/j_follower.json \
   ~/.cache/huggingface/lerobot/calibration/robots/so_follower/
```

## 校准后验证

### 1. 遥操作测试

校准完成后，运行遥操作验证主从臂跟随是否正常：

```bash
unset PYTHONPATH
conda activate lerobot

lerobot-teleoperate \
  --teleop.type=so101_leader \
  --teleop.port=<LEADER_PORT> \
  --teleop.id=j_leader \
  --robot.type=so101_follower \
  --robot.port=<FOLLOWER_PORT> \
  --robot.id=j_follower
```

**验证要点**：

- 拖拽主臂时，从臂能实时跟随
- 6 个关节都能正常活动，包括 `wrist_roll`
- 夹爪能完全张开和闭合（已 patch 为 100% 扭矩）
- 没有电机通信失败的报错

### 2. 单臂测试（可选）

如果只想测试主臂自身是否工作：

```bash
unset PYTHONPATH
conda activate lerobot

lerobot-teleoperate \
  --teleop.type=so101_leader \
  --teleop.port=<LEADER_PORT> \
  --teleop.id=j_leader
```

此时没有从臂连接，只会读取并显示主臂状态。退出按 `Ctrl+C`。

## 常见问题

### Q1: 校准过程中某个电机通信失败

**现象**：程序报错退出，或某个关节无法活动。  
**处理**：

1. 检查 USB 线是否插紧
2. 检查电源是否足够（SO-101 需要较大电流）
3. 重新上电后再次运行校准
4. 已应用电机通信容错 patch，单个电机失败时只会打印 warning，不会整体崩溃

### Q2: 校准后从臂不跟随主臂

**可能原因**：

- 主臂和从臂的校准文件不匹配
- 串口对应关系搞反
- `wrist_roll` 方向/范围不一致

**处理**：

1. 删除旧的校准文件，重新校准两臂
2. 用 `lerobot-find-port` 再次确认主从臂串口

### Q3: 夹爪无法完全张开

**处理**：已 patch 夹爪扭矩为 100%。如果仍有问题，检查夹爪机械结构是否卡滞。

### Q4: 每次都要重新校准吗？

**是的**。参考项目明确说明：每次断电重新连接后都要校准。如果同一 session 内只是重启程序，校准文件还在，通常可以复用。

## 下一步

校准和遥操作验证通过后，进入 [03-teleoperation.md](03-teleoperation.md) 进行正式遥操作测试，或直接开始 [04-recording.md](04-recording.md) 录制数据。
