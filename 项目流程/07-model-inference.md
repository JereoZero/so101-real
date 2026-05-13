# 7. 模型推理

## 模型导出

训练生成的 checkpoint 目录结构为 `checkpoints/{step}/pretrained_model/`。推理时代码期望 `pretrained_model/` 内部的文件在目标目录的根层级，因此需要"去壳"复制：

```bash
# V1/V2（25000步）
mkdir -p /home/jer/ws/workspace/models/smolvla210_put_3_in
cp -r checkpoints/025000/pretrained_model/* /home/jer/ws/workspace/models/smolvla210_put_3_in/

# V3（40000步）
mkdir -p /home/jer/ws/workspace/models/smolvla_v3_infer
cp -r checkpoints/040000/pretrained_model/* /home/jer/ws/workspace/models/smolvla_v3_infer/
```

**注意**：不能保留 `pretrained_model/` 这层目录，否则推理时报 FileNotFoundError。

## 推理版本

训练产出多个模型版本，推理时分别使用：

| 版本 | 来源 | 步数 | 推理时长 | 用途 |
|------|------|------|----------|------|
| V1/V2 | smolvla210 | 25000 | 60秒 | 三色全覆盖基准 |
| V3 | smolvla_v3_run2 | 40000 | 120秒 | V3 评估，更长推理时间 |

## 推理命令

### V1/V2

```bash
sudo chmod 666 /dev/ttySO101_FOLLOWER

lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttySO101_FOLLOWER \
    --robot.id=j_follower \
    --robot.fixed_joints="{wrist_roll: -67.74}" \
    --robot.cameras="{camera1: {type: opencv, index_or_path: 2, fps: 30, width: 640,
      height: 480, fourcc: YUYV}, camera2: {type: opencv, index_or_path: 0, fps: 30,
      width: 640, height: 480, fourcc: MJPG}}" \
    --display_data=false \
    --dataset.repo_id=local/eval_smolvla210 \
    --dataset.root=/home/jer/ws/workspace/datasets/eval_smolvla210 \
    --dataset.single_task="put small green block in plate" \
    --dataset.episode_time_s=60 \
    --dataset.push_to_hub=false \
    --resume=true \
    --policy.path=/home/jer/ws/workspace/models/smolvla210_put_3_in
```

### V3

仅需修改两个参数：
```bash
--dataset.episode_time_s=120 \
--policy.path=/home/jer/ws/workspace/models/smolvla_v3_infer
```

## 推理参数说明

| 参数 | 值 | 说明 |
|------|-----|------|
| `--policy.path` | 模型目录 | 导出的模型权重路径 |
| `--dataset.single_task` | 语言指令 | 模型据此确定抓取哪种颜色的方块 |
| `--dataset.episode_time_s` | 60 / 120 | 推理时长，V3 更长因为训练步数更多 |
| `--resume` | true | 推理模式下复用 eval 数据集，不创建新数据 |
| `--display_data` | false | 推理时不预览以减少开销 |

## 推理时的摄像头配置

推理命令中摄像头名称使用 `camera1` / `camera2`（而非录制时的 `front` / `top`），因为训练好的模型期望这两个名称。对应的 eval 数据集也需要将 feature 名称从 `front`/`top` 改为 `camera1`/`camera2`。

## 颜色切换

推理时通过修改 `--dataset.single_task` 参数切换目标颜色。三种指令分别对应：

```bash
# 绿色
--dataset.single_task="put small green block in plate"
# 葡萄紫
--dataset.single_task="put small grape block in plate"
# 橙色
--dataset.single_task="put small orange block in plate"
```

## eval_ 数据集前缀

LeRobot 要求推理数据集以 `eval_` 开头，用于区分训练集和评估集。通过软链接解决：

```bash
ln -sf /home/jer/ws/workspace/datasets/smolvla210 \
       /home/jer/ws/workspace/datasets/eval_smolvla210
```