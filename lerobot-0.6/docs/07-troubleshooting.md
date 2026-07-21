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
