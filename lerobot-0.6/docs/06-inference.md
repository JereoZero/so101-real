# 06. 推理部署

> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)  
> 参考项目文档：[07-model-inference.md](https://github.com/JereoZero/so101-real/blob/main/%E9%A1%B9%E7%9B%AE%E6%B5%81%E7%A8%8B/07-model-inference.md)

## 前置条件

- 已完成 [05-training.md](05-training.md)
- 模型已训练完成
- 机械臂已连接并上电（与录制时同一环境最佳）

## 模型导出

训练生成的 checkpoint 目录结构为 `checkpoints/{step}/pretrained_model/`。LeRobot 推理时期望目标目录根层级包含模型文件，因此需要先"去壳"复制：

```bash
# 例如使用 40000 步的 checkpoint
mkdir -p /home/j/ws/so101/checkpoints/so101_smolvla_infer
cp -r outputs/so101_smolvla/checkpoints/040000/pretrained_model/* \
  /home/j/ws/so101/checkpoints/so101_smolvla_infer/
```

**注意**：不能保留 `pretrained_model/` 这层目录，否则推理时会报 `FileNotFoundError`。

## 真机推理（v0.6.0 推荐：`lerobot-rollout`）

LeRobot v0.6.0 新增了专门的真机部署 CLI `lerobot-rollout`，本项目已包装为 [`src/scripts/rollout.py`](../../src/scripts/rollout.py)。它替代了 v0.5.x 常用的 `lerobot-eval` 真机推理方式，支持自主运行、DAgger 人机回环、连续录制等多种策略。

### 基础自主推理

```bash
cd /home/j/ws/so101
unset PYTHONPATH
conda activate lerobot

python src/scripts/rollout.py \
  --strategy.type=base \
  --policy.path=/home/j/ws/so101/checkpoints/so101_smolvla_infer \
  --robot.type=so101_follower \
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3E121987-if00 \
  --robot.id=j_follower \
  --robot.fixed_joints="{wrist_roll: -27.82}" \
  --robot.cameras="{front: {type: opencv, index_or_path: /dev/v4l/by-id/usb-icSpring_icspring_camera-video-index0, fps: 30, width: 640, height: 480, fourcc: YUYV}, top: {type: opencv, index_or_path: /dev/v4l/by-id/usb-icSpring_icspring_camera_202404160005-video-index0, fps: 30, width: 640, height: 480, fourcc: MJPG}}" \
  --task="put small green block in plate" \
  --duration=60 \
  --display_data=false
```

### 按模型类型选择推理方式

| 模型 | 推理速度 | 建议配置 | 5070 显存 |
|------|---------|---------|----------|
| ACT / Diffusion | 快 | 默认 `sync` | 充足 |
| SmolVLA | 较慢 | 建议 `rtc` | 刚好 |
| Pi0 / Pi0.5 / EO1 | 很慢 | 必须 `rtc`，但 12GB 可能仍吃紧 | 不足 |

### 慢速 VLA 使用 RTC 推理

SmolVLA、Pi0、Pi0.5 等模型推理较慢，建议开启 Real-Time Chunking：

```bash
python src/scripts/rollout.py \
  --strategy.type=base \
  --inference.type=rtc \
  --inference.rtc.execution_horizon=10 \
  --policy.path=/home/j/ws/so101/checkpoints/so101_smolvla_infer \
  --robot.type=so101_follower \
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3E121987-if00 \
  --robot.id=j_follower \
  --robot.fixed_joints="{wrist_roll: -27.82}" \
  --robot.cameras="{front: {type: opencv, index_or_path: /dev/v4l/by-id/usb-icSpring_icspring_camera-video-index0, fps: 30, width: 640, height: 480, fourcc: YUYV}, top: {type: opencv, index_or_path: /dev/v4l/by-id/usb-icSpring_icspring_camera_202404160005-video-index0, fps: 30, width: 640, height: 480, fourcc: MJPG}}" \
  --task="put small green block in plate" \
  --duration=60
```

### 关键参数说明

| 参数 | 参考值 | 说明 |
|------|--------|------|
| `--strategy.type` | base | 自主运行；可选 sentry/highlight/dagger/episodic |
| `--inference.type` | sync / rtc | sync 为每控制周期调用一次策略；rtc 为慢速 VLA 实时 chunk 推理 |
| `--policy.path` | 导出后的模型目录 | 必须去掉 `pretrained_model/` 外壳 |
| `--task` | 语言指令 | 模型据此确定抓取哪种颜色的方块 |
| `--duration` | 60 / 300 | 推理时长（秒），0 表示无限运行 |
| `--display_data` | false | 推理时不预览，减少开销 |
| `--fps` | 30 | 控制频率 |

### DAgger 人机回环（模型纠错迭代）

v0.6.0 的 `lerobot-rollout` 支持 DAgger 模式：模型执行时如果出错，人可以接管主臂纠正，纠正数据自动保存用于再训练。

```bash
python src/scripts/rollout.py \
  --strategy.type=dagger \
  --strategy.num_episodes=20 \
  --inference.type=rtc \
  --inference.rtc.execution_horizon=10 \
  --policy.path=/home/j/ws/so101/checkpoints/so101_smolvla_infer \
  --robot.type=so101_follower \
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3E121987-if00 \
  --robot.id=j_follower \
  --teleop.type=so101_leader \
  --teleop.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3E121553-if00 \
  --teleop.id=j_leader \
  --dataset.repo_id=local/so101_dagger_corrections \
  --dataset.single_task="put small green block in plate" \
  --dataset.push_to_hub=false
```

## 颜色切换

通过 `--task` 切换目标颜色：

```bash
# 绿色
--task="put small green block in plate"

# 紫色
--task="put small grape block in plate"

# 橙色
--task="put small orange block in plate"
```

> 颜色名称必须与训练数据中的语言指令一致。

## 兼容说明：v0.5.x 的 `lerobot-eval` 方式

v0.5.x 常用的真机推理命令形如：

```bash
lerobot-eval \
  --robot.type=so101_follower \
  --policy.path=... \
  --dataset.repo_id=local/eval_xxx \
  ...
```

在 v0.6.0 中，`lerobot-eval` 主要用于**仿真 benchmark 评估**（LIBERO-plus、RoboTwin 2.0 等），而真机部署推荐使用 `lerobot-rollout`。如果某些脚本或教程仍使用 `lerobot-eval` 接真机，建议替换为 `lerobot-rollout`。

## 验证推理

- [ ] 机械臂能自动完成抓放任务
- [ ] 对物体位置、颜色变化有一定泛化能力
- [ ] 失败时能安全停止（按 `Ctrl+C`）

## 迭代优化

如果效果不佳：

1. 增加数据多样性
2. 使用 DAgger 收集失败场景的人为纠正数据
3. 尝试不同策略（Diffusion / SmolVLA）
4. 增加训练步数或调整固定关节角度

## 安全提示

推理时从臂会自主运动，请确保：

- 周围没有易碎物品和人员
- 从臂活动范围内没有障碍物
- 随时可以按 `Ctrl+C` 停止
- 首次推理时建议降低 `--duration`，先观察几轮
