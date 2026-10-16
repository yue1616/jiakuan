# jiakuan 当前网络严格复测工具

## 解决什么问题

`jiakuan` 的 GitHub Actions 在美国 Azure 环境里测活。美国测试通过，只能说明节点从那台测试机上可用，不能代表从你实际使用的中国大陆网络也可用；而原项目最低下载速度仅为 `70,000 B/s`（约 0.56 Mbps），对日常网页使用过低。

这个工具不再把美国 CI 的结果当成你的最终结果，而是在你平时使用代理的那台 Windows 电脑和当前网络上测试。只有满足下面条件的节点才会输出：

- 至少 2 个独立 HTTPS 探测目标成功；
- HTTPS 探测耗时不高于默认 700 ms；
- 实际代理下载速度不低于默认 250,000 B/s（约 2 Mbps）；
- 第一轮和第二轮复测都通过；
- 遵守项目现有的 v2rayN 导出兼容过滤，不为节点伪造 TLS/SNI。

## 安装与运行

把 `scripts/test_local_network.py` 复制到你仓库的 `scripts/` 目录。**不要用本包里的脚本替换仓库现有的 `main_v2.py`**；工具会复用仓库现有解析器与 sing-box 配置函数。

在仓库根目录打开 PowerShell，先安装依赖：

```powershell
python -m pip install -r scripts/requirements.txt
```

若项目根目录有 `runtime\sing-box.exe`，直接执行：

```powershell
python scripts/test_local_network.py --min-speed 250000 --max-latency 700 --workers 4
```

如果 sing-box 不在项目 `runtime` 目录，请指定可执行文件的完整路径：

```powershell
python scripts/test_local_network.py --sing-box "C:\完整路径\sing-box.exe" --min-speed 250000 --max-latency 700 --workers 4
```

默认输入为当前仓库的在线订阅：

`https://cdn.jsdelivr.net/gh/yue1616/jiakuan@main/output/v2ray.txt`

若在线订阅下载失败，先在浏览器把 `v2ray.txt` 保存到本机，再用下面方式指定文件：

```powershell
python scripts/test_local_network.py --input "C:\路径\v2ray.txt" --sing-box "C:\完整路径\sing-box.exe" --min-speed 250000 --max-latency 700 --workers 4
```

## 输出在哪里

默认生成到 `output/local-verified/`：

- `v2ray-local-tested.txt`：Base64 订阅文本；
- `v2ray-local-tested-links.txt`：明文分享链接，可全选复制后在 v2rayN 中通过“从剪贴板导入分享链接”单独导入；
- `local-test-report.json`：通过数量、协议、延迟和测速结果。

工具不会覆盖 GitHub 上的 `output/v2ray.txt`。先单独导入本地测试结果，确认实际浏览网页正常后再使用。

## 限制

这是当前机器、当前网络的实测，不是永久保证。公共免费节点可能随时过期或变慢；换网络/运营商后应重新测试。若严格复测剩下很少节点，这不是工具误报成功，而是该网络下真正能稳定通过这些条件的节点少。要更快，可以把 `--min-speed` 提高到 `400000`（约 3.2 Mbps）；若只想增加数量，可以调低，但可用性和速度可能下降。
