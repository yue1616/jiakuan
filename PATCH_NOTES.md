# jiakuan v2rayN 导出修复补丁

将压缩包中的 `scripts/main_v2.py` 与 `scripts/test_parsers.py` 覆盖到仓库相同路径。

## 改动

- VLESS 导出显式写出 `encryption=none` 和默认 `type=tcp`，避免输出 `?#name` 空查询。
- VMess 解析/导出保留 TLS fingerprint、ALPN 和 allowInsecure 等字段，并修正 `verify_cert` 的反向语义兼容。
- 修复 URI query 经 `parse_qs` 解码后又二次 `unquote` 的问题，避免传输路径/服务名含百分号编码时被改写。
- 对 Trojan、Hysteria2、TUIC、AnyTLS 的账号字段执行严格 URI 编码，降低密码包含 `/ ? # @` 等保留字符时解析异常的风险。
- 单元测试新增导出→重新解析往返校验，以及 Hysteria2 特殊字符密码测试。

## 本地检查范围

- Python 语法解析通过。
- 对压缩包内的 634 条 `v2ray.txt` 链接做了解析和重新导出结构检查：输入解析失败 0、重新导出解析失败 0；原导出中发现 7 条 VLESS `?#` 空查询链接。
- 对 19 个协议/传输样本执行了导出往返结构测试，均通过。
- 本地没有运行真实 sing-box 核心；测试过程对 `sing-box check` 调用做了模拟。因此请在 GitHub Actions 中执行真实的配置校验，并用 v2rayN 抽查。

此补丁不能单独保证公开免费节点稳定；它主要修复可确认的订阅导出/解析缺陷。95% 的连接失败还需结合 v2rayN 的具体报错和所选 core/版本，确认是否由节点过期或客户端兼容性造成。
