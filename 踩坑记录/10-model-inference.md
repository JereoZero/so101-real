# 10. 模型推理

## 10.1 模型版本概览

训练产出多个版本，推理时使用不同版本进行对比：

| 版本 | 来源 | 训练步数 | 推理时长 | 模型路径 |
|------|------|----------|----------|----------|
| V1/V2 | smolvla210 | 25000 | 60秒 | `smolvla210_put_3_in` |
| V3 | smolvla_v3_run2 | 40000 | 120秒 | `smolvla_v3_infer` |

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

# V3 版本导出
mkdir -p /home/jer/ws/workspace/models/smolvla_v3_infer
cp -r checkpoints/040000/pretrained_model/* /home/jer/ws/workspace/models/smolvla_v3_infer/
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

推理时长增加到 120 秒：

```bash
    --dataset.episode_time_s=120 \
    --policy.path=/home/jer/ws/workspace/models/smolvla_v3_infer
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
| `--dataset.episode_time_s` | 推理时长，V1/V2用60秒，V3用120秒 |
| `--resume=true` | **复用现有 eval 数据集，不创建新数据集** |
| `--display_data=false` | 关闭 GUI 预览减少开销 |

---

## 10.7 推理时 GPU 使用

推理默认使用 GPU（配置中 `device: cuda`），无需额外配置。

推理速度慢的常见原因：
- 相机帧率不足（非模型问题）
- 缺少真实摄像头的警告信息可忽略
- 模型加载（906MB）需要一定时间