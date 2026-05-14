# 10. 模型推理

## 10.1 模型版本概览

训练产出多个版本，推理时使用不同版本进行对比：

| 版本 | 来源 | 训练步数 | 模型路径 |
|------|------|----------|----------|
| V1/V2 | smolvla210 | 25000 | `smolvla210_put_3_in` |
| V3 | smolvla_v3_run2 | 40000 | `smolvla_v3_infer_18k` / `smolvla_v3_infer_22k` |

---

## 10.2 pretrained_model 文件位置问题

**现象**：推理时报：
```
FileNotFoundError: [Errno 2] No such file or directory: 'pretrained_model/config.json'
```

**原因**：LeRobot 保存的 checkpoint 结构是 `checkpoints/xxx/pretrained_model/config.json`。如果直接复制 `checkpoints/xxx/` 整个目录，路径会变成 `xxx/pretrained_model/config.json`，但推理代码期望 `xxx/config.json`。

**解决**：复制时只取 `pretrained_model/` 内部的文件，放到目标目录的根层级：

```bash
# V1/V2 版本导出
mkdir -p /home/jer/ws/workspace/models/smolvla210_put_3_in
cp -r checkpoints/025000/pretrained_model/* /home/jer/ws/workspace/models/smolvla210_put_3_in/
```

**绝对不要**保留 `pretrained_model/` 这层目录。

---

## 10.3 推理数据集名称必须以 `eval_` 开头

**现象**：推理时报：
```
ValueError: Your dataset name does not begin with 'eval_' (smolvla210), but a policy is provided
```

**原因**：LeRobot 强制推理时数据集名称以 `eval_` 开头，用于区分训练数据集和评估/推理数据集。

**解决**：创建软链接：

```bash
ln -sf /home/jer/ws/workspace/datasets/smolvla210 \
       /home/jer/ws/workspace/datasets/eval_smolvla210
```

然后在推理命令中：
```bash
--dataset.repo_id=local/eval_smolvla210 \
--dataset.root=/home/jer/ws/workspace/datasets/eval_smolvla210 \
```

---

## 10.4 推理时 Feature 不匹配

**现象**：推理时报：
```
Feature mismatch: Missing ['observation.images.camera1', 'observation.images.camera2']
Extra: ['observation.images.front', 'observation.images.top']
```

**原因**：训练好的 policy 期望 `camera1`/`camera2`，但数据集用的是 `front`/`top`。

**解决**：需要修改推理时使用的 eval 数据集，将 feature 名称改为 `camera1`/`camera2`。包括：
1. 修改 `meta/info.json` 中的 features 名称
2. 重命名 `videos/` 下的文件夹（`observation.images.front` → `observation.images.camera1`）
3. 修改 episode parquet 的列名
4. 修改 `stats.json` 的 key
5. 推理命令中相机配置也用 `camera1`/`camera2`

```bash
--robot.cameras="{camera1: {type: opencv, index_or_path: 2, ...}, camera2: {type: opencv, index_or_path: 0, ...}}"
```

---

## 10.5 推理命令模板

### V1/V2 版本（25000步）

推理时长为 60 秒，可覆盖三色：

```bash
sudo chmod 666 /dev/ttySO101_FOLLOWER

lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower \
    --robot.fixed_joints="{wrist_roll: -67.74}" \
    --robot.cameras="{camera1: {type: opencv, index_or_path: 2, fps: 30, width: 640, height: 480, fourcc: YUYV}, camera2: {type: opencv, index_or_path: 0, fps: 30, width: 640, height: 480, fourcc: MJPG}}" \
    --display_data=false \
    --dataset.repo_id=local/eval_smolvla210 \
    --dataset.root=/home/jer/ws/workspace/datasets/eval_smolvla210 \
    --dataset.single_task="put small green block in plate" \
    --dataset.episode_time_s=60 \
    --dataset.push_to_hub=false \
    --resume=true \
    --policy.path=/home/jer/ws/workspace/models/smolvla210_put_3_in
```

### V3 版本（40000步）

推理时长增加到 300 秒（5分钟），因为 V3 模型更稳健，可以处理更连续的动作：

```bash
sudo chmod 666 /dev/ttySO101_FOLLOWER

lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower \
    --robot.fixed_joints="{wrist_roll: -67.74}" \
    --robot.cameras="{camera1: {type: opencv, index_or_path: 2, fps: 30, width: 640, height: 480, fourcc: YUYV}, camera2: {type: opencv, index_or_path: 0, fps: 30, width: 640, height: 480, fourcc: MJPG}}" \
    --display_data=false \
    --dataset.repo_id=local/eval_smolvla210 \
    --dataset.root=/home/jer/ws/workspace/datasets/eval_smolvla210 \
    --dataset.single_task="put small green block in plate" \
    --dataset.episode_time_s=300 \
    --dataset.push_to_hub=false \
    --resume=true \
    --policy.path=/home/jer/ws/workspace/models/smolvla_v3_infer_18k
```

### 颜色切换

只需修改 `--dataset.single_task`：

| 颜色 | single_task |
|------|-------------|
| 绿色 | `"put small green block in plate"` |
| 葡萄紫 | `"put small grape block in plate"` |
| 橙色 | `"put small orange block in plate"` |

---

## 10.6 推理参数说明

| 参数 | 说明 |
|------|------|
| `--policy.path` | 训练好的模型路径 |
| `--dataset.single_task` | 语言指令，模型据此定位目标颜色 |
| `--dataset.episode_time_s` | 推理时长，根据实测情况调整 |
| `--resume=true` | **复用现有 eval 数据集，不创建新数据集** |
| `--display_data=false` | 关闭 GUI 预览减少开销 |

---

## 10.7 V3 各 Checkpoint 测试结果

V3 训练产出了多个 checkpoint（每 2000 步保存），经过逐一测试对比，18k 表现最好：

| 步数 | 表现 | 备注 |
|------|------|------|
| 10k | 基础可用 | |
| 14k | 较好 | |
| 16k | 不错 | |
| **18k** | ✅ **最强** | 所有 checkpoint 中表现最佳 |
| 20k | 不错 | 接近 18k |
| 22k | ✅ 较好 | 仅次于 18k，备选 |
| 24k | 一般 | |
| 26k | 非常一般 | |
| 28k | 较好 | 不如 18k/22k |
| 30k | 一般 | |
| 32k | 一般 | |
| 34k | 较差 | |
| 36k | 较差 | |
| 38k | 一般 | |
| 40k | 一般 | |

**结论**：推荐使用 **18k** 推理，**22k** 作为备选。更多步数不代表更好效果，模型在中间阶段泛化最均衡。务必对比多个 checkpoint 再做选择。

模型导出：
```bash
# 18k 推理模型
mkdir -p /home/jer/ws/workspace/models/smolvla_v3_infer_18k
cp -r /home/jer/ws/workspace/models/smolvla_v3_run2/checkpoints/018000/pretrained_model/* /home/jer/ws/workspace/models/smolvla_v3_infer_18k/

# 22k 推理模型
mkdir -p /home/jer/ws/workspace/models/smolvla_v3_infer_22k
cp -r /home/jer/ws/workspace/models/smolvla_v3_run2/checkpoints/022000/pretrained_model/* /home/jer/ws/workspace/models/smolvla_v3_infer_22k/
```

---

## 10.8 推理时 GPU 使用

推理默认使用 GPU（配置中 `device: cuda`），无需额外配置。模型会自动加载到 CUDA GPU 上进行推理。

推理速度慢的常见原因：
- 相机帧率不足（非模型问题）
- 缺少真实摄像头的警告信息可忽略
- 模型加载（906MB）需要一定时间

---

## 10.9 爪子马达红灯问题

**现象**：遥控爪子时，某些角度会导致夹爪马达亮红灯。红灯后暂时还能控制，但退出程序后再进入录制/推理时找不到该马达，必须断电重启才能恢复。

**原因**：
1. 爪子转动角度超过安全范围，触发过载保护
2. 某些角度阻力大，导致电流超标

**建议**：
- 一旦发现红灯，立即将爪子回到中间位置再退出程序
- 遥控时使用更慢的速度
- 确认 `wrist_roll: -67.74` 在安全范围内
- 推理前先断电重启一次确保所有马达正常