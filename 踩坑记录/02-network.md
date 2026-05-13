# 2. 网络相关问题

## 2.1 GitHub 克隆极慢 / 超时

**现象**：`git clone` GitHub 仓库速度 ~30 KiB/s，经常超时断开。

**尝试过的方案与结果**：

| 方案 | 结果 |
|------|------|
| 直连 | ping 能通，但 HTTPS 协议不通，clone 失败 |
| 配置 Git 代理（http.proxy） | 某些环境下反而导致 HTTPS 连接超时 |
| shallow clone（`--depth 1`） | 可缓解但不能根治，大仓库仍然超时 |
| 切换 SSH 协议代替 HTTPS | 如果 SSH 端口被封则无效 |

**根本原因**：GitHub 在国内的 HTTPS 连接极不稳定，间歇性被干扰。

**最终方案**：
- **优先在能正常上网的机器上下载**，再通过 U 盘拷贝到工作机器
- **Docker 镜像加速**：Docker pull 使用 `docker.1ms.run` 镜像源
- 如需直连时配置 Git 代理：
  ```bash
  git config --global http.proxy http://127.0.0.1:7890
  git config --global https.proxy http://127.0.0.1:7890
  # 取消代理
  git config --global --unset http.proxy
  git config --global --unset https.proxy
  ```

---

## 2.2 Git clone GnuTLS 错误

**现象**：`git clone` 报 GnuTLS 相关错误，SSL/TLS 握手失败。

**解决**：

```bash
# 方案1：重装 GnuTLS 库
sudo apt install --reinstall libgnutls30

# 方案2：使用 SSH 协议代替 HTTPS
git clone git@github.com:xxx/xxx.git
```

---

## 2.3 HuggingFace 网络不可达

**现象**：训练/下载模型时报：
```
[Errno 101] Network is unreachable
```
无法连接 huggingface.co。

**原因**：HuggingFace 在国内被墙，直连无法访问。

**解决方案**（按推荐顺序）：

1. **离线模式训练（最稳定）**：
   ```bash
   HF_HUB_OFFLINE=1 lerobot-train ...
   ```
   前提：模型（model.safetensors 906MB）和数据集已提前下载到本地。

2. **在能上网的机器上下载模型，U 盘拷贝到工作机**：
   这是本项目最终使用的方式——在网络通的 Windows/Mac 上访问 huggingface.co 下载预训练模型文件，U 盘传到 Ubuntu。

3. **配置 HF 镜像（不总是稳定）**：
   ```bash
   export HF_ENDPOINT=https://hf-mirror.com
   ```

4. **使用代理**：
   ```bash
   export HTTP_PROXY=http://127.0.0.1:7890
   export HTTPS_PROXY=http://127.0.0.1:7890
   ```

---

## 2.4 ping 能通但 HTTPS 不通

**现象**：`ping 8.8.8.8` 通，`ping github.com` 通，但 `git clone`、`wget`、浏览器访问 HTTPS 网站全部失败或极慢。

**原因**：DNS 解析正常、ICMP 包不受限制，但 TCP 443 端口（HTTPS）被干扰。这是国内网络环境的典型特征。

**排查方法**：

```bash
# 测试 ICMP（大概率通）
ping -c 4 github.com

# 测试 HTTPS（大概率不通或极慢）
curl -v https://github.com

# 查看 DNS
cat /etc/resolv.conf
```

**解决**：要么用代理，要么换到能上网的机器下载后 U 盘拷贝。