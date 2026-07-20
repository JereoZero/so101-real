# 04. 数据录制

> 参考项目：[JereoZero/so101-real](https://github.com/JereoZero/so101-real)  
> 参考项目文档：[05-data-collection.md](https://github.com/JereoZero/so101-real/blob/main/%E9%A1%B9%E7%9B%AE%E6%B5%81%E7%A8%8B/05-data-collection.md)

## 前置条件

- 已完成 [03-teleoperation.md](03-teleoperation.md)
- 遥操作正常
- 已确定任务流程（如：抓取绿色方块放入盘子）
- 摄像头、桌面、光照等物理环境已布置好

## 录制命令

使用 LeRobot 自带的 `lerobot-record`（项目包装脚本为 `src/scripts/record.py`）：

```bash
cd /home/j/ws/so101
unset PYTHONPATH
conda activate lerobot

python src/scripts/record.py \
  --robot.type=so101_follower \
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3E121987-if00 \
  --robot.id=j_follower \
  --robot.cameras="{front: {type: opencv, index_or_path: /dev/v4l/by-id/usb-icSpring_icspring_camera-video-index0, fps: 30, width: 640, height: 480, fourcc: YUYV}, top: {type: opencv, index_or_path: /dev/v4l/by-id/usb-icSpring_icspring_camera_202404160005-video-index0, fps: 30, width: 640, height: 480, fourcc: MJPG}}" \
  --teleop.type=so101_leader \
  --teleop.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3E121553-if00 \
  --teleop.id=j_leader \
  --display_data=true \
  --dataset.repo_id=local/so101_pick_place \
  --dataset.push_to_hub=false \
  --dataset.num_episodes=10 \
  --dataset.single_task="put small green block in plate" \
  --dataset.episode_time_s=20 \
  --dataset.reset_time_s=9999
```

### 关键参数说明

| 参数 | 参考值 | 说明 |
|------|--------|------|
| `--display_data` | true | 实时预览摄像头和关节状态，便于观察录制质量 |
| `--dataset.episode_time_s` | 20 | 单条 episode 最大录制时长（秒），手动按键可提前结束 |
| `--dataset.reset_time_s` | 9999 | 复位阶段超长时间，实现完全手动控制准备下一条 |
| `--dataset.push_to_hub` | false | 不上传 HuggingFace，仅本地保存 |
| `--dataset.single_task` | 语言指令 | 任务描述，也是训练/推理时的提示词 |
| `--dataset.num_episodes` | 10 | 本次计划录制的 episode 数量 |
| `--dataset.root` | 本地路径 | v0.6.0 新增，指定数据集本地存储目录；不指定则存到 HF 缓存 |

### v0.6.0 新特性：自动时间戳与流式编码

- **自动时间戳**：v0.6.0 每次新建录制都会把 `repo_id` 追加时间戳，例如 `local/so101_pick_place` 会变成 `local/so101_pick_place_20260720_123456`。训练或回放时需要用这个**实际生成的 repo_id**，或者在录制时通过 `--dataset.root` 指定稳定本地路径。
- **流式视频编码**（可选）：v0.6.0 支持 `--dataset.streaming_encoding=true`，录制时实时编码视频，保存 episode 几乎无等待。CPU 较强时可开启：
  ```bash
  --dataset.streaming_encoding=true \
  --dataset.encoder_threads=2
  ```
- **视频编码参数路径变化**：v0.5.x 的 `--dataset.vcodec` 已改为 `--dataset.rgb_encoder.vcodec`，例如：
  ```bash
  --dataset.rgb_encoder.vcodec=h264
  ```

### 关于 `wrist_roll` 固定角度

参考项目 v0.5.1 中使用了 `--robot.fixed_joints="{wrist_roll: -67.74}"` 来固定手腕旋转角度。LeRobot v0.6.0 原版的 `SOFollowerConfig` 没有 `fixed_joints` 字段，但本项目已通过 patch 把它加回来了。

固定 `wrist_roll` 的配置已写入 [`src/configs/so101.yaml`](../../src/configs/so101.yaml)：

```yaml
robot:
  type: so101_follower
  fixed_joints:
    wrist_roll: -27.82
```

效果：

- 遥操作时，无论你如何旋转主臂的 `wrist_roll`，从臂的 `wrist_roll` 都会被覆盖为 `-27.82°`。
- 录制数据里的 `action.wrist_roll` 也始终是 `-27.82°`，模型不需要学习这个关节。
- 如果你希望模型学习 `wrist_roll`，把 `fixed_joints` 留空或删除即可。

> 配置里的角度单位是 **度**（因为 `use_degrees: true`）。

## 录制键位

| 按键 | 功能 |
|------|------|
| **→ 右箭头** | 结束当前阶段（录制 → 复位 / 复位 → 录制） |
| **← 左箭头** | 放弃当前 episode，重新录制本条的复位阶段 |
| **ESC** | 完全停止录制 |

## 录制流程

```text
启动录制 → 校准从臂 → 进入复位阶段
    ↓
循环：手动摆场景 → 按 → 开始录制 → 操作主臂完成抓放 → 按 → 结束录制
    ↓
按 ESC 停止 → 回放验证数据质量 → 整理数据集
```

## 数据多样性策略

为了让模型具备良好的泛化能力，录制时应注意：

### 1. 物体位置多样化

| 区域 | 建议占比 | 说明 |
|------|---------|------|
| 核心区（桌面中心约 25cm × 25cm） | ~70% | 正常操作区域 |
| 边缘/极端区 | ~30% | 让模型学习关节在极限角度附近的状态 |

### 2. 初始状态多样化

每次 episode 开始时机械臂的初始位置**不固定**：

- 居中起始
- 上次停止位置附近
- 故意偏置（如方块在左时手臂初始靠右）

### 3. 干扰物与颜色

- 同一种任务录制多组：目标 only、+1 干扰、+2 干扰
- 干扰物可以是不同颜色方块、圆形块、更大体积方块
- 通过 `--dataset.single_task` 区分目标颜色

## 数据回放验证

录制完成后应立即回放，确认数据质量：

### 1. 驱动机械臂回放（会实际运动从臂）

v0.6.0 中使用独立的 `lerobot-replay` 命令来回放数据集到真实机器人：

```bash
unset PYTHONPATH
conda activate lerobot

lerobot-replay \
  --robot.type=so101_follower \
  --robot.port=/dev/serial/by-id/usb-1a86_USB_Single_Serial_5B3E121987-if00 \
  --robot.id=j_follower \
  --dataset.repo_id=local/so101_pick_place \
  --dataset.episode=0
```

> 注意：`lerobot-record` 不再支持 `--replay` 参数，v0.5.x 的旧命令需要改为 `lerobot-replay`。

### 2. 纯可视化查看（不驱动机器臂）

```bash
lerobot-dataset-viz \
  --repo-id local/so101_pick_place \
  --episode-index 0
```

## 数据集整理

录制数据默认存储在 HuggingFace 缓存目录，建议整理到项目 `data/` 目录：

```bash
# 查看录制数据位置
ls ~/.cache/huggingface/lerobot/local/so101_pick_place

# 复制到项目目录（可选）
mkdir -p /home/j/ws/so101/data
rsync -av ~/.cache/huggingface/lerobot/local/so101_pick_place/ \
  /home/j/ws/so101/data/so101_pick_place/
```

合并多组数据时，可使用 LeRobot 的数据集合并工具，或保持多集分别训练。

## 迭代录制

参考项目经验：前几次录制通常需要迭代调整。建议：

- 每次录制少量 episode（如 10 条）
- 立即回放验证
- 根据效果调整固定关节角度、光照、摄像头位置等
- 数据集 ID 带版本号（如 `so101_pick_place_v1`、`v2`）方便追溯

## 下一步

数据量足够且质量验证通过后，进入 [05-training.md](05-training.md) 训练模型。
