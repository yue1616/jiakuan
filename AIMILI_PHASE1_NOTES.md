# jiakuan / Aimili 改造第一阶段说明

本阶段先保留现有 jiakuan 订阅生成器，解决“单次探测成功、导入 v2rayN 后仍大量 -1”的误入主池风险。

## 本阶段代码改动

- 活性探测不再命中第一个 URL 就停止；三个探测目标全部记录结果，并统计 HTTPS 目标命中数。
- 对第一轮通过基础隧道、测速达标且未检测到 MITM 的节点做第二轮独立复测。
- 主订阅中的节点必须在两轮中均满足：至少两个独立 HTTPS 目标返回 200/204、获取出口 IP、测速不少于 70 KB/s、无断流、无 MITM。
- 第二轮仍可响应但未满足全部严格要求的节点，只导出到 `output/candidates/`，名称带“候选”，不会混入 `output/v2ray.txt`、`output/clash.yaml` 或 `output/singbox.json`。
- 若本轮严格池为空，保留上一次主订阅，避免用空文件覆盖；候选池仍可单独更新。
- GitHub Actions 加入并发串行化，并在更新后清理候选池的 jsDelivr 缓存。

## 订阅地址

- 严格主池：原有 `output/v2ray.txt`、`output/clash.yaml`、`output/singbox.json`。
- 候选池：`output/candidates/v2ray.txt`、`output/candidates/clash.yaml`、`output/candidates/singbox.json`。

## 重要范围说明

这不是完整的 Aimili 四协议 VPN 服务端改造。所上传的 jiakuan 压缩包是 GitHub Actions 节点订阅生成器，没有 Aimili 管理网页、服务端管理模块或现成的 OpenVPN / SoftEther SSL-VPN / SSTP / L2TP 连接管理代码。当前补丁不会伪造那些功能，也不会安装或修改服务器网络路由。完整的多协议服务端需要在独立阶段加入、审查并测试实际客户端适配器和管理 UI。

## 验证

- Python 语法编译通过。
- 解析器、协议导出往返、去重、VLESS 兼容性及严格池门槛单元测试通过。
- 此执行环境没有 `maxminddb` 依赖或 Linux sing-box 二进制，因此本地测试中对这些环境依赖做了模拟；这不等于真实 sing-box 网络测活。GitHub Actions 有安装步骤，应以新一轮 Actions 的真实 `sing-box check` 和探测报告为准。
