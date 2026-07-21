# SO101 机器人学习项目

> 用幻尔 SO-101 双臂机械臂 + LeRobot + SmolVLA，让机器人学会自主抓放方块。
>
> 硬件：NVIDIA RTX 5070 12GB | AMD Ryzen 7 3700X | B450M 主板 | 96GB DDR4 | Ubuntu 22.04

---

## 💡 小贴士

> 本仓库的每一步操作、踩坑记录、源码修改都有详细文档。你可以直接把项目地址喂给 AI（如 ChatGPT、Claude、Trae 等），让它帮你看每一步的流程、坑点和代码改动，自己再决定哪些要改、哪些不改。
>
> 示例提示词：
>
> *"请阅读这个 GitHub 项目 https://github.com/JereoZero/so101-real 的文档和代码，帮我梳理从零开始搭建 SO-101 + LeRobot 项目的完整流程，重点标注踩坑点和需要修改的代码。"*

---

## 🚀 LeRobot v0.6.0（最新版本）

> **👉 完整代码和文档在 [`lerobot-0.6/`](./lerobot-0.6/) 目录下。**

基于 LeRobot **v0.6.0** 的新版本项目，利用了 v0.6 的全新特性：

| 特性 | 说明 |
|------|------|
| `lerobot-rollout` | 替代旧版 `lerobot-eval`，支持真机推理、DAgger 人机回环、连续录制 |
| DAgger 原生支持 | 模型出错时人类接管纠正，数据自动保存再训练 |
| RTC 实时推理 | `--inference.type=rtc`，慢速 VLA 也能实时控制 |
| 流式编码 | `--dataset.streaming_encoding=true`，episode 保存几乎无等待 |
| `lerobot-replay` | 独立命令回放数据集到真机 |

### 当前进展

- [x] 硬件连接、校准、遥操作（wrist_roll 锁定 -27.82°）
- [x] 数据录制完成：**200 条**示教数据（v1-1 ~ v1-20，合并为 `v1_merged`）
- [x] torchcodec 兼容问题解决（改用 `--dataset.video_backend=pyav`）
- [x] SmolVLA 测试训练通过（batch=36，显存 ~10.1GB）
- [ ] **SmolVLA v1-1 训练中**（10k 步，~3h）
- [ ] 真机推理部署（`lerobot-rollout` + RTC）
- [ ] DAgger 人机回环迭代

### 文档导航

详细操作文档见 [`lerobot-0.6/docs/`](./lerobot-0.6/docs/)：

1. [硬件连接与上电](./lerobot-0.6/docs/01-hardware-setup.md)
2. [机械臂校准](./lerobot-0.6/docs/02-calibration.md)
3. [遥操作测试](./lerobot-0.6/docs/03-teleoperation.md)
4. [数据录制](./lerobot-0.6/docs/04-recording.md)
5. [模型训练](./lerobot-0.6/docs/05-training.md)
6. [推理部署](./lerobot-0.6/docs/06-inference.md)
7. [常见问题排查](./lerobot-0.6/docs/07-troubleshooting.md)

---

## 📂 仓库目录说明

本仓库按 LeRobot 版本分目录，结构对称：

```
so101-real/
├── lerobot-0.6/     ← v0.6.0（最新），代码 + 文档，活跃开发中
├── lerobot-0.5/     ← v0.5.1（老版本），踩坑记录 + 项目流程，已完成
├── images/          ← 项目展示图片/GIF
└── README.md        ← 本文件
```

| 目录 | LeRobot 版本 | 内容 | 状态 |
|------|-------------|------|------|
| [`lerobot-0.6/`](./lerobot-0.6/) | **v0.6.0（最新）** | 代码、文档、脚本 | 活跃开发中 |
| [`lerobot-0.5/`](./lerobot-0.5/) | v0.5.1（老版本） | 踩坑记录、项目流程 | 已完成 |

> v0.6 的很多设置是在 v0.5 基础上搭建的，老版本的踩坑记录和流程更详细，建议对照阅读。

---

## LeRobot v0.5.1（老版本）

> 以下内容基于 LeRobot **v0.5.1**，已完成。v0.6.0 的很多设置是在此基础上搭建的，流程更详细，建议对照阅读。

### 项目概述

从零开始的完整实机项目：装系统、刷 BIOS、装驱动，到遥操作录制数据、训练模型、推理部署。所有文档基于实际操作经历撰写。

### 任务

让机器人学会在随机位置抓取小方块并放入盘子中。任务核心是"精准抓放"。

| 物品 | 尺寸 | 说明 |
|------|------|------|
| 小方块 | 3.5cm 边长 | 三种颜色：绿色、葡萄紫、橙色 |
| 盘子 | 8.5cm 直径 | 小盘子，放置精度要求高 |

### 工作流程

```
遥操作录制专家示教数据 → SmolVLA 模仿学习训练 → 语言指令驱动自主推理
```

### 技术栈

| 层 | 技术 |
|----|------|
| 算法 | SmolVLA（基于预训练 VLM 的模仿学习策略） |
| 框架 | LeRobot v0.5.1 |
| 深度学习 | PyTorch 2.10 + CUDA 13.0 |
| 机器人 | 幻尔 SO-101 双臂机械臂（主从遥操作） |
| 感知 | 双摄像头（爪子视角 + 顶部视角，普通 RGB） |

### 项目亮点

- **完整从零搭建**：从装系统、刷 BIOS、装驱动到训练推理全流程
- **新硬件适配**：RTX 5070 (Blackwell) + 老主板 BIOS 更新 + open 版驱动
- **非定点操作**：盘子和方块随机放置，不是固定位置
- **多场景泛化**：三种颜色 × 三种干扰级别 × 光照变化
- **框架源码修改**：修复了 LeRobot 的 4 处问题
- **多版本迭代**：数据录到 v6，训练跑了 3 轮，推理有 V1/V2/V3

### 数据与训练（v0.5.1）

| 指标 | 数值 |
|------|------|
| 训练数据 | 210 条（每色约 70 条） |
| 录制迭代 | 6 轮（v1→v6） |
| 训练轮次 | 3 轮（10000 → 40000 → 40000 V3） |
| 推理模型 | V1/V2（25000步/60s）+ V3（40000步/300s） |

### 老版本文档

- 遇到了问题 → [`lerobot-0.5/踩坑记录/`](./lerobot-0.5/踩坑记录/)
- 想了解详细流程 → [`lerobot-0.5/项目流程/`](./lerobot-0.5/项目流程/)

## 项目展示

### 物理环境

<img src="images/环境.jpg" alt="实验环境" width="600">

<img src="images/干扰环境.jpg" alt="干扰环境示例" width="600">

### 数据采集回放

![数据回放](images/数据回放.gif)

### 模型训练

<img src="images/训完模型.jpg" alt="训练完成" width="600">

### 连续推理演示

![连续推理演示](images/连续推理演示demo.gif)

---

## 快速导航

- **LeRobot v0.6.0（最新）** → [`lerobot-0.6/`](./lerobot-0.6/)
- **LeRobot v0.5.1（老版本）** → [`lerobot-0.5/`](./lerobot-0.5/)
- 版本区分说明 → [VERSION_NOTICE.md](./VERSION_NOTICE.md)

> **参考文档**：同济子豪兄的 LeRobot 系列教程：[子豪兄SO101教程](https://zihao-ai.feishu.cn/wiki/TS6swApHbinx01kHDi5cf5n5n8c)
