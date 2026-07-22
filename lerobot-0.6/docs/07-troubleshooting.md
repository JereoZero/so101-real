# 07. 常见问题排查

## 1. 串口找不到

```bash
ls /dev/tty*
ls /dev/serial/by-id/
dmesg | tail -20
```

- 检查 USB 线是否连接
- 检查电机板是否上电
- 检查是否有权限（用户是否在 `dialout` 组）
- 检查是否被其他程序占用

## 2. 校准失败 / 范围不对

- 确认已应用 patch：`python apply_patches.py`
- 删除旧校准文件后重新校准：
  ```bash
  rm -rf ~/.cache/huggingface/lerobot/calibration/teleoperators/so_leader/j_leader.json
  rm -rf ~/.cache/huggingface/lerobot/calibration/robots/so_follower/j_follower.json
  ```
- 检查是否有电机 ID 错误或通信失败

## 3. 夹爪无力

- 确认 gripper 扭矩 patch 已应用：`python apply_patches.py`
- 检查电机是否过热保护
- 检查夹爪机械结构是否卡滞

## 4. 遥操作时从臂不跟随

- 检查串口是否正确
- 检查校准文件是否存在
- 检查主从臂是否搞反
- 检查电源是否足够（双臂同时运动电流较大）

## 5. 录制时复位阶段无法控制主臂

- 确认 `lerobot_record.py` 的 teleop patch 已应用：`python apply_patches.py`
- 检查 `--dataset.reset_time_s` 是否设置得足够大

## 6. 训练时 CUDA 报错

- 检查 PyTorch CUDA 是否可用：
  ```bash
  python -c "import torch; print(torch.cuda.is_available())"
  ```
- 检查 GPU 显存是否足够（RTX 5070 12GB）
- 降低 `--batch_size` 或开启 `--policy.use_amp=true`

## 7. 训练时报 `FileNotFoundError`

- 检查 `--policy.path` 是否指向正确的本地模型目录
- 检查模型目录下是否直接包含 `config.json`、`model.safetensors` 等文件
- 推理前需要去掉 `pretrained_model/` 外壳（见 [06-inference.md](06-inference.md)）

## 8. 推理时动作不稳定

- 降低推理频率
- 检查 observation 预处理
- 增加数据量或训练步数
- 检查固定关节角度是否与录制时一致

## 9. 摄像头打不开或画面异常

- 检查摄像头 USB 是否松动
- 检查 by-id 路径是否变化
- 尝试改用 index 方式打开
- 检查 `fourcc` 是否与摄像头支持的格式一致（front=YUYV，top=MJPG）

## 10. 电机通信偶发失败但流程继续

这是正常现象。已应用电机通信容错 patch，单个电机失败时会打印 warning，不会导致整个流程崩溃。如果失败频繁，请检查：

- USB 线质量
- 电源功率
- 电机板固件版本

## 11. 校准时报 `TypeError` 或 `ValueError: Negative values are not allowed`

### 11.1 `TypeError: {'shoulder_pan': Motor(...), ...}`

**现象**：执行 `lerobot-calibrate` 后，在 "Recording positions" 阶段报错：

```text
TypeError: {'shoulder_pan': Motor(id=1, ...), ...}
```

**原因**：SO-101 patch 需要把 `wrist_roll` 加入校准范围，但 v0.6.0 的 `record_ranges_of_motion` 只接受电机名称列表，不接受 `self.bus.motors` 这个 dict。

**解决**：确保 `apply_patches.py` 已更新到最新版本并重新执行：

```bash
cd /home/j/ws/so101
python apply_patches.py
```

patch 后 `so_leader.py` 和 `so_follower.py` 里会传 `list(self.bus.motors.keys())`，而不是 `self.bus.motors`。

### 11.2 `ValueError: Negative values are not allowed: -865`

**现象**：校准范围记录完成后，写入电机时报错：

```text
ValueError: Negative values are not allowed: -865
```

**原因**：`wrist_roll` 是 360° 旋转关节，校准过程中越过 0/4095 边界后，`set_half_turn_homings()` 计算出的范围最小值会变成负数，而 Feetech 电机不接受负的位置限制。

**解决**：重新执行最新版 `apply_patches.py`，patch 会把 `wrist_roll` 的 `range_min` / `range_max` 裁剪到 `[0, 4095]` 后再写入电机。

## 12. v0.5.x 命令/参数在 v0.6.0 中报错

常见兼容性问题：

| v0.5.x 用法 | v0.6.0 对应方式 | 说明 |
|------------|----------------|------|
| `--robot.fixed_joints` | `robot.fixed_joints`（需 patch） | 原版 v0.6.0 的 `SOFollowerConfig` 无此字段，本项目 patch 已恢复 |
| `lerobot-record --replay` | `lerobot-replay` | 回放已独立为单独命令 |
| `lerobot-eval` 接真机 | `lerobot-rollout` | v0.6.0 中 `lerobot-eval` 主要用于仿真 benchmark |
| `--policy.pretrained_model_path` | `--policy.path` | 训练/推理加载本地模型时参数名已改 |
| `--dataset.vcodec` | `--dataset.rgb_encoder.vcodec` | 视频编码参数路径已改 |
| `eval_freq` | `env_eval_freq` | 训练配置中评估频率参数已改名 |
| `--dataset.repo_id='["a","b"]'` | `lerobot-edit-dataset --operation.type=merge` | v0.6.0 禁用了 MultiLeRobotDataset，需先物理合并 |

## 13. 训练卡在 0% 不动 / torchcodec 加载失败

### 现象

训练启动后卡在 `Training: 0%| | 0/1000 [00:20<?, ?step/s]`，GPU 显存和利用率都很低，日志里有大量 `OSError: libavutil.so.XX: cannot open shared object file` 或 `Could not load libtorchcodec` 错误。

### 原因

LeRobot v0.6.0 默认使用 `torchcodec` 作为视频解码后端。`torchcodec` 需要 FFmpeg 动态库（libavutil/libavcodec 等），而 conda 环境中虽然安装了 FFmpeg 8，但由于 `libopenvino.so` 依赖 `CXXABI_1.3.15`（系统 `libstdc++.so.6` 最高只到 `1.3.13`），导致 `libtorchcodec_core8.so` 加载失败。`find_spec("torchcodec")` 返回 `True`（包已安装），但实际导入时崩溃，训练进程卡在数据加载阶段。

### 解决

训练时加 `--dataset.video_backend=pyav` 强制使用 PyAV 后端：

```bash
HF_HUB_OFFLINE=1 python src/scripts/train.py \
  --dataset.video_backend=pyav \
  ...（其他参数不变）
```

PyAV 已安装在 lerobot conda 环境中（`av==15.1.0`），功能完整可用，只是比 torchcodec 稍慢（对训练速度影响极小，因为视频解码不是瓶颈）。

### 验证

```bash
# 测试 pyav 视频解码
conda run -n lerobot python -c "
from lerobot.datasets.lerobot_dataset import LeRobotDataset
ds = LeRobotDataset('local/so101_grape_put_v1_merged', root='/home/j/ws/so101/data/so101_grape_put_v1_merged', video_backend='pyav')
print(f'OK: {len(ds)} frames, {ds.num_episodes} episodes')
"
```

### 长期修复（可选）

如果需要让 torchcodec 正常工作，需要解决 `CXXABI_1.3.15` 缺失问题：

```bash
# 方案 1：升级系统 libstdc++（风险较大，不推荐）
# 方案 2：设置 LD_PRELOAD 使用 conda 环境的 libstdc++（需确认版本足够新）
# 方案 3：卸载 openvino（如果不使用）
conda remove -n lerobot openvino
```

当前项目推荐直接使用 `--dataset.video_backend=pyav`，无需额外操作。

## 14. 推理时报 `Visual feature mismatch`

### 现象

```text
ValueError: Visual feature mismatch between policy and robot hardware
```

模型期望的摄像头名称为 `camera1`、`camera2`、`camera3`，但机器人实际提供的是 `front`、`top`。

### 原因

SmolVLA 预训练模型使用 3 个摄像头（`camera1`/`camera2`/`camera3`），但 SO-101 实际只有 2 个摄像头（`front`/`top`），名称不匹配。

### 解决

两个参数缺一不可：

```bash
# 1. 重命名摄像头：front→camera1, top→camera2
--rename_map='{"observation.images.front": "observation.images.camera1", "observation.images.top": "observation.images.camera2"}'

# 2. 声明有 1 个空摄像头位（模型期望 3 个，实际只有 2 个）
--policy.empty_cameras=1
```

## 15. 推理卡在 "Loading policy"

### 现象

运行推理命令后，卡在 `Loading policy from '...'` 不动，没有任何进度，也不报错退出。

### 原因

LeRobot 推理时默认会联网下载 `chat_template.jinja` 文件。如果网络不通或 HuggingFace 无法访问，就会卡住。

### 解决

命令前加 `HF_HUB_OFFLINE=1`：

```bash
HF_HUB_OFFLINE=1 python src/scripts/rollout.py ...
```

## 16. `episodic` 策略报错 `--dataset.repo_id` 必填

### 现象

```text
ValueError: episodic strategy requires --dataset.repo_id to be set
```

### 原因

LeRobot v0.6.0 的 `episodic` 策略会录制数据，必须指定数据集名称。

### 解决

```bash
--strategy.type=episodic \
--dataset.repo_id=local/rollout_xxx \
--dataset.push_to_hub=false \
--dataset.single_task="put grape block in plate"
```

数据集名称必须以 `rollout_` 开头，否则会报：

```text
ValueError: Dataset names for rollout must start with 'rollout_'
```

## 17. `episodic` 策略的组数和时长参数

### 现象

```bash
# 错误：这些参数不存在
--strategy.num_episodes=25
--strategy.episode_duration_s=30
```

### 原因

`episodic` 策略的 `EpisodicStrategyConfig` 没有 `num_episodes` 和 `episode_duration_s` 字段。这些参数来自 `DatasetRecordConfig`。

### 解决

使用 `--dataset.*` 前缀：

```bash
# 正确
--dataset.num_episodes=25    # 总组数
--dataset.episode_time_s=30  # 每组推理时长（秒）
--dataset.reset_time_s=15    # 组间复位时长（秒）
```

## 18. 训练时 `--output_dir` 参数不存在

### 现象

```text
Error: unrecognized arguments: --output_dir
```

### 原因

v0.6.0 移除了 `--output_dir` 参数，数据集存储路径改由 `--dataset.root` 控制，模型输出路径由 `--policy.path` 控制。

### 解决

```bash
# v0.5.x 旧写法
--output_dir=outputs/so101_smolvla

# v0.6.0 新写法
--dataset.root=/home/j/ws/so101/data/so101_grape_put_v1
--policy.path=outputs/so101_smolvla/checkpoints/last/pretrained_model
```

## 19. 训练时 `--steps` 参数行为变化

### 现象

恢复训练时，指定 `--steps=20000` 但模型只跑了 10000 步就停了。

### 原因

v0.6.0 中 `--steps` 指定的是**总步数**（不是额外步数）。如果已经训练了 10000 步，`--steps=20000` 只会再跑 10000 步。

### 解决

```bash
# 第一次训练：0→20000 步
--steps=20000

# 从 10000 步恢复训练到 20000 步
--resume=true \
--config_path=outputs/so101_smolvla/checkpoints/010000/pretrained_model/train_config.json \
--steps=20000
```

## 20. 训练时数据集合并失败

### 现象

```text
ValueError: MultiLeRobotDataset is disabled in v0.6.0
```

### 原因

v0.6.0 禁用了 `MultiLeRobotDataset`，不能通过 `--dataset.repo_id='["a","b"]'` 直接加载多个数据集。

### 解决

使用 `lerobot-edit-dataset --operation.type=merge` 先物理合并：

```bash
lerobot-edit-dataset \
  --operation.type=merge \
  --operation.repo_ids='["local/ds1","local/ds2"]' \
  --operation.roots='["/path/to/ds1","/path/to/ds2"]' \
  --new_repo_id=local/merged \
  --new_root=/path/to/merged
```

## 21. 训练时视频编码参数报错

### 现象

```text
Error: unrecognized arguments: --dataset.vcodec
```

### 原因

v0.6.0 中视频编码参数路径从 `--dataset.vcodec` 改为 `--dataset.rgb_encoder.vcodec`。

### 解决

```bash
# v0.5.x
--dataset.vcodec=h264

# v0.6.0
--dataset.rgb_encoder.vcodec=h264
```

## 22. 训练配置中 `eval_freq` 报错

### 现象

```text
Error: unrecognized arguments: --eval_freq
```

### 原因

v0.6.0 中 `eval_freq` 改名为 `env_eval_freq`。

### 解决

```bash
# v0.5.x
eval_freq=1000

# v0.6.0
env_eval_freq=1000
```

## 23. 训练时 `sac` 策略报错

### 现象

```text
Error: unrecognized strategy: sac
```

### 原因

v0.6.0 中 `sac` 策略改名为 `gaussian_actor`。

### 解决

```bash
# v0.5.x
--policy.type=sac

# v0.6.0
--policy.type=gaussian_actor
```

## 24. 推理时 `--duration=0` 不退出

### 现象

设置 `--duration=0` 后模型一直运行不停止。

### 说明

`--duration=0` 表示无限运行模式，这是正常行为。用于手动换场景测试时很方便。如果希望自动结束，改成一个正数（秒）：

```bash
--duration=300   # 5 分钟后自动退出
```

如果要自动运行多轮带复位，使用 `episodic` 策略代替 `base` 策略。

## 25. 机械臂电机连接不稳定（部分电机找不到）

### 现象

```
RuntimeError: FeetechMotorsBus motor check failed on port '...':

Missing motor IDs:
  - 4 (expected model: 777)

Full found motor list:
{1: 777, 2: 777, 3: 777, 5: 777, 6: 777}
```

### 原因

- 电机电源不稳定（供电不足或接触不良）
- USB 转串口线松动
- 电机板固件异常

### 解决

1. 重新上电（关闭电源，等 5 秒再开）
2. 检查 USB 线连接
3. 如果特定电机反复掉线，检查该电机的接线
4. 运行 `ls /dev/serial/by-id/` 确认串口设备存在

## 26. 训练时数据增强参数变化

### 现象

训练时图片转换相关参数名称变化。

### 解决

```bash
# v0.6.0 启用图片增强
--dataset.image_transforms.enable=true
--dataset.image_transforms.random_order=true
```

## 27. 训练时 batch_size 和显存

### 说明

RTX 5070 (12GB) 上训练 SmolVLA，推荐：

```bash
--batch_size=36
```

如果显存不足（OOM），降低到 24 或 16。训练时建议开启 AMP 混合精度：

```bash
--policy.use_amp=true
```

## 28. 训练时 PyTorch 版本要求

### 说明

LeRobot v0.6.0 要求 PyTorch ≥ 2.7。如果在旧环境中安装，需要先升级：

```bash
pip install --upgrade torch torchvision
```

验证：

```bash
python -c "import torch; print(torch.__version__)"
# 应输出 2.7.x 或更高
```
