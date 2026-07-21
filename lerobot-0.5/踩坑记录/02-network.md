# 2. 网络相关问题

如果 GitHub、HuggingFace 直连不稳定或镜像不好用，不用在 Ubuntu 机器上折腾。

最简单的方案：在网络好的笔记本上下载需要的文件（模型权重、git 仓库 zip、数据集等），然后用 LocalSend 通过局域网传到 Ubuntu 机器。

> 笔记本负责下载，Ubuntu 只负责算。