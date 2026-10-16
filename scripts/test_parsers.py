#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单元自测: 全协议解析器 + sing-box check 配置合法性 + 分类逻辑"""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main_v2 as mv

BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# 按当前操作系统选择正确的 sing-box 文件名；CI 为 Linux，不能硬编码 .exe。
SB_NAME = "sing-box.exe" if os.name == "nt" else "sing-box"
SB = os.path.join(BASEDIR, "runtime", SB_NAME)
if not os.path.exists(SB):
    SB = os.path.join(BASEDIR, ".sb-probe", SB_NAME)

# ══════════ 测试样本 (覆盖用户全部协议) ══════════
SAMPLES = {
    # VLESS + Reality + Vision (最高误杀率的协议组合)
    "vless_reality_vision": "vless://b831381d-6324-4d53-ad4f-8cda48b30811@example.com:443?encryption=none&flow=xtls-rprx-vision&security=reality&sni=www.example.com&fp=chrome&pbk=SbVKOEMjK0sIlbwg4akyBg5mL5KZwwB-ed4eEE7YnRc&sid=0123abcd&type=tcp#TestVlessReality",
    # VLESS + WS + TLS (CDN 中转常见)
    "vless_ws_tls": "vless://b831381d-6324-4d53-ad4f-8cda48b30811@cdn.example.com:443?encryption=none&security=tls&sni=cdn.example.com&type=ws&host=cdn.example.com&path=%2Fws#TestVlessWs",
    # VLESS + grpc
    "vless_grpc": "vless://b831381d-6324-4d53-ad4f-8cda48b30811@example.com:443?encryption=none&security=tls&sni=example.com&type=grpc&serviceName=grpc-svc#TestVlessGrpc",
    # VLESS + httpupgrade
    "vless_httpupgrade": "vless://b831381d-6324-4d53-ad4f-8cda48b30811@example.com:80?encryption=none&security=none&type=httpupgrade&path=%2Fupgrade&host=example.com#TestVlessHU",
    # VLESS + h2
    "vless_h2": "vless://b831381d-6324-4d53-ad4f-8cda48b30811@example.com:443?encryption=none&security=tls&sni=example.com&type=h2&path=%2Fh2path&host=h2.example.com#TestVlessH2",
    # VMess (ws + tls)
    "vmess_ws": "vmess://" + mv.base64.b64encode(json.dumps({
        "v": "2", "ps": "TestVmess", "add": "vm.example.com", "port": "443",
        "id": "b831381d-6324-4d53-ad4f-8cda48b30811", "aid": "0",
        "scy": "auto", "net": "ws", "type": "none", "host": "vm.example.com",
        "path": "/vmws", "tls": "tls", "sni": "vm.example.com",
        "fp": "chrome", "alpn": "h2,http/1.1", "allowInsecure": True}).encode()).decode(),
    # VMess legacy (tcp, no tls, aid>0)
    "vmess_legacy": "vmess://" + mv.base64.b64encode(json.dumps({
        "v": "2", "ps": "TestVmessLegacy", "add": "legacy.example.com", "port": "8080",
        "id": "b831381d-6324-4d53-ad4f-8cda48b30811", "aid": "64",
        "scy": "auto", "net": "tcp", "type": "none", "tls": ""}).encode()).decode(),
    # VMess grpc
    "vmess_grpc": "vmess://" + mv.base64.b64encode(json.dumps({
        "v": "2", "ps": "TestVmessGrpc", "add": "grpc.example.com", "port": "443",
        "id": "b831381d-6324-4d53-ad4f-8cda48b30811", "aid": "0",
        "scy": "auto", "net": "grpc", "path": "grpc-svc", "tls": "tls"}).encode()).decode(),
    # Trojan (sni + allowInsecure)
    "trojan": "trojan://pass%40word123@example.com:443?sni=www.example.com&allowInsecure=1&type=tcp#TestTrojan",
    # Trojan ws
    "trojan_ws": "trojan://pass123@example.com:443?sni=example.com&type=ws&path=%2Ftjws&host=example.com#TestTrojanWs",
    # SS SIP002 (明文 userinfo)
    "ss_sip002": "ss://aes-256-gcm:cGFzc3dvcmQ%3D@ss.example.com:8388#TestSS",
    # SS legacy base64
    "ss_legacy": "ss://" + mv.base64.urlsafe_b64encode(b"aes-256-gcm:pass123").decode().rstrip("=") + "@legacy-ss.example.com:8388#TestSSLegacy",
    # SS 2022 (密钥格式)
    "ss_2022": "ss://2022-blake3-aes-128-gcm:8J3gp0S5y2X0YVpDZH2YvA%3D%3D@ss2022.example.com:8388#TestSS2022",
    # Hysteria2 (sni + insecure + obfs)
    "hy2": "hy2://pass123@hy2.example.com:443?sni=hy2.example.com&insecure=1&obfs=salamander&obfs-password=obfspw#TestHy2",
    # Hysteria2 端口跳跃 (mport 区间+单端口混合)
    "hy2_hop": "hysteria2://pass123@hop.example.com:443?sni=hop.example.com&insecure=1&mport=2087-2097,443#TestHy2Hop",
    # TUIC v5
    "tuic": "tuic://b831381d-6324-4d53-ad4f-8cda48b30811:pass123@tuic.example.com:443?congestion_control=bbr&udp_relay_mode=native&alpn=h3&sni=tuic.example.com&allow_insecure=1#TestTuic",
    # AnyTLS
    "anytls": "anytls://pass123@anytls.example.com:443?sni=anytls.example.com&insecure=1#TestAnytls",
    # IPv6 字面量 (旧版正则必死的场景)
    "vless_ipv6": "vless://b831381d-6324-4d53-ad4f-8cda48b30811@[2001:db8::1]:443?encryption=none&security=tls&sni=v6.example.com&type=tcp#TestIPv6",
    # 域名含端口非常规 (解析应成功)
    "vless_path_edge": "vless://b831381d-6324-4d53-ad4f-8cda48b30811@edge.example.com:8443?encryption=none&security=none&type=ws&path=%2Fed#TestEdge",
}

FAIL = []

def run_test():
    print("=" * 70)
    print("阶段1: 协议解析器单元测试 (17 个样本)")
    print("=" * 70)
    outbounds = {}
    for name, uri in SAMPLES.items():
        parsed = mv.parse_node_uri(uri)
        if not parsed:
            FAIL.append(f"[PARSE-FAIL] {name}: {uri[:60]}")
            print(f"  ❌ {name}: 解析失败")
            continue
        ob, server, port, proto = parsed
        # 出口必备字段 (端口跳跃节点: server_port 被 server_ports 替代)
        if ob.get("server_port") is not None:
            assert ob["server"] == server and ob["server_port"] == port
        else:
            assert ob.get("server_ports"), "既无 server_port 也无 server_ports"
        outbounds[name] = ob
        print(f"  ✅ {name}: {proto} @ {server}:{port}")
        # 额外结构断言
        if name == "vless_reality_vision":
            assert ob.get("flow") == "xtls-rprx-vision", "flow 丢失"
            assert ob["tls"]["reality"]["public_key"], "reality pbk 丢失"
            assert ob["tls"]["utls"]["fingerprint"] == "chrome", "utls fp 丢失"
        if name == "hy2_hop":
            assert ob.get("server_ports"), "mport 端口跳跃丢失"
            # 实测约束: 不能有裸单端口
            for p in ob["server_ports"]:
                assert ":" in p, f"裸单端口 {p} 会导致 sing-box FATAL"
        if name == "tuic":
            assert ob.get("uuid") and ob.get("password") and ob.get("congestion_control")
        if name == "anytls":
            assert ob.get("password") and ob["tls"]["enabled"]

    print()
    print("=" * 70)
    print(f"阶段2: sing-box check 配置合法性 ({len(outbounds)} 个 outbound)")
    print("=" * 70)
    import subprocess, tempfile
    for name, ob in outbounds.items():
        cfg = mv.build_test_config(ob, 53000 + (hash(name) % 500))
        # 清理测试用多余字段 (domain_strategy 等不存在)
        try:
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
                json.dump(cfg, f)
                path = f.name
            r = subprocess.run([SB, "check", "-c", path], capture_output=True, text=True, timeout=15)
            if r.returncode == 0:
                print(f"  ✅ {name}: check PASS")
            else:
                err = (r.stderr or r.stdout or "").strip().splitlines()
                err_short = err[-1][:100] if err else "?"
                FAIL.append(f"[CHECK-FAIL] {name}: {err_short}")
                print(f"  ❌ {name}: check FAIL → {err_short}")
        finally:
            try:
                os.remove(path)
            except Exception:
                pass

    print()
    print("=" * 70)
    print("阶段3: 网络类型分类逻辑 (离线)")
    print("=" * 70)
    cases = [
        # (ip, asn, org, 期望 net_type)
        ("104.16.1.1", 13335, "cloudflare", "cdn"),             # CF 段硬判
        ("172.67.10.1", 13335, "Cloudflare, Inc.", "cdn"),
        ("8.8.8.8", 15169, "Google LLC", "cdn"),                 # Google 公共 DNS 段
        ("23.94.10.1", 36352, "ColoCrossing", "datacenter"),    # IDC ASN
        ("211.72.35.1", 3462, "Chunghwa Telecom", "residential"),# 台湾中华电信家宽
        ("61.220.50.1", 3462, "CHT", "residential"),
        ("219.85.10.1", 17676, "Softbank BB", "residential"),   # 日本软银家宽
        ("81.19.66.1", 6679, "Skynet", "unknown"),               # 无明显特征
    ]
    for ip, asn, org, expect in cases:
        got, conf = mv.classify_network_type(ip, None, asn, org, None)
        mark = "✅" if got == expect else ("⚠️" if expect == "unknown" else "❌")
        if got != expect and expect != "unknown":
            FAIL.append(f"[CLASSIFY] {ip} {org}: 期望 {expect} 实得 {got}")
        print(f"  {mark} {ip} ({org}) → {got} conf={conf}")

    print()
    print("=" * 70)
    if FAIL:
        print(f"共 {len(FAIL)} 项失败:")
        for f in FAIL:
            print(f"  - {f}")
        sys.exit(1)

    # 阶段4: 去重指纹回归测试——同 endpoint 的不同凭据/传输参数不能共享结果。
    print()
    print("阶段4: 节点去重指纹回归测试")
    base = {"type": "vless", "tag": "one", "server": "node.example", "server_port": 443,
            "uuid": "user-a", "tls": {"enabled": True, "server_name": "a.example"},
            "transport": {"type": "ws", "path": "/ws", "headers": {"Host": "a.example"}}}
    same = dict(base, tag="renamed")
    other_credentials = dict(base, uuid="user-b")
    other_sni = dict(base, tls={"enabled": True, "server_name": "b.example"})
    other_path = dict(base, transport={"type": "ws", "path": "/other", "headers": {"Host": "a.example"}})
    key = mv.node_dedup_key(base, "node.example", 443, "vless")
    assert key == mv.node_dedup_key(same, "node.example", 443, "vless"), "显示名称不应影响去重"
    assert key != mv.node_dedup_key(other_credentials, "node.example", 443, "vless"), "不同 UUID 不可合并"
    assert key != mv.node_dedup_key(other_sni, "node.example", 443, "vless"), "不同 SNI 不可合并"
    assert key != mv.node_dedup_key(other_path, "node.example", 443, "vless"), "不同传输路径不可合并"
    print("  ✅ 相同配置可去重；凭据、SNI、传输路径不同则独立测活")

    print()
    print("阶段5: v2rayN 导出链接往返测试")
    for sample_name, original_ob in outbounds.items():
        exported = mv.outbound_to_v2ray_link(original_ob, "roundtrip")
        assert exported, f"{sample_name}: 导出结果为空"
        reparsed = mv.parse_node_uri(exported)
        assert reparsed, f"{sample_name}: 导出的链接无法再次解析: {exported[:100]}"
        ob2, server2, port2, proto2 = reparsed
        server1 = original_ob["server"]
        port1 = original_ob.get("server_port")
        if port1 is None:
            port1 = int(str(original_ob["server_ports"][0]).split(":")[0])
        key1 = mv.node_dedup_key(original_ob, server1, port1, original_ob["type"])
        key2 = mv.node_dedup_key(ob2, server2, port2, proto2)
        assert key1 == key2, f"{sample_name}: 导出后连接参数发生变化"
        print(f"  ✅ {sample_name}: 导出后协议参数保持一致")

    # 保留对 URI 保留字符密码的覆盖，避免 / ? # @ 被误判成 URI 分隔符。
    special_password_node = {
        "type": "hysteria2", "tag": "node", "server": "hy2.example.com",
        "server_port": 443, "password": "a/b?c#d@e",
        "tls": {"enabled": True, "server_name": "hy2.example.com", "insecure": False},
    }
    special_link = mv.outbound_to_v2ray_link(special_password_node, "special-password")
    special_parsed = mv.parse_node_uri(special_link)
    assert special_parsed and special_parsed[0]["password"] == special_password_node["password"], \
        "Hysteria2 特殊字符密码在导出/导入往返中发生变化"
    print("  ✅ Hysteria2 特殊字符密码可以安全往返")

    print()
    print("阶段6: v2rayN/Xray 不兼容 VLESS 过滤测试")
    unsafe_public_ip = {
        "type": "vless", "tag": "public-plain", "server": "203.0.113.10",
        "server_port": 443, "uuid": "b831381d-6324-4d53-ad4f-8cda48b30811",
        "transport": {"type": "ws", "path": "/ws"},
    }
    # 文档网段不是 global，因此再用实际 public-IP 语义测试；地址只作为纯单元样本，不发起网络连接。
    unsafe_public_ip["server"] = "8.8.4.4"
    assert mv.outbound_to_v2ray_link(unsafe_public_ip, "unsafe") == "", \
        "公网 IP 且没有 TLS/REALITY 的 VLESS 应从 v2rayN 订阅过滤"
    print("  ✅ 公网 IP + 无 TLS/REALITY 的 VLESS 会被过滤")

    safe_tls = dict(unsafe_public_ip, server="8.8.4.4", tls={"enabled": True, "server_name": "node.example"})
    safe_link = mv.outbound_to_v2ray_link(safe_tls, "safe-tls")
    assert safe_link and "security=tls" in safe_link, "带 TLS 的 VLESS 不应被误过滤"
    print("  ✅ 公网 IP + TLS 的 VLESS 保留")

    safe_domain = dict(unsafe_public_ip, server="node.example")
    safe_domain_link = mv.outbound_to_v2ray_link(safe_domain, "domain-node")
    assert safe_domain_link, "域名型 VLESS 不应仅因没有 TLS 被此规则误过滤"
    print("  ✅ 域名型 VLESS 不会被此过滤规则误伤")

    print()
    print("阶段7: 最终去重不会误删共享出口 IP 的备用入口")
    uri_a = "vless://b831381d-6324-4d53-ad4f-8cda48b30811@edge-a.example.com:443?encryption=none&security=tls&sni=edge.example.com&type=ws&host=edge.example.com&path=%2Fws#edge-a"
    uri_a_renamed = uri_a.rsplit("#", 1)[0] + "#another-name"
    uri_b = "vless://b831381d-6324-4d53-ad4f-8cda48b30811@edge-b.example.com:443?encryption=none&security=tls&sni=edge.example.com&type=ws&host=edge.example.com&path=%2Fws#edge-b"
    key_a = mv.final_node_dedup_key({"raw": uri_a, "exit_ip": "198.51.100.10", "port": 443})
    key_a_renamed = mv.final_node_dedup_key({"raw": uri_a_renamed, "exit_ip": "198.51.100.10", "port": 443})
    key_b = mv.final_node_dedup_key({"raw": uri_b, "exit_ip": "198.51.100.10", "port": 443})
    assert key_a == key_a_renamed, "只改显示名称不应生成重复连接配置"
    assert key_a != key_b, "共享出口 IP/端口的不同入口不能被当作同一个连接配置"
    print("  ✅ 相同配置不同名称合并；不同服务器入口即使共享出口 IP/端口也会保留")
    print("全部测试通过 ✅")


def write_report(status: str, error: str = ""):
    report_dir = os.path.join(BASEDIR, "output")
    os.makedirs(report_dir, exist_ok=True)
    report = {
        "status": status,
        "sample_count": len(SAMPLES),
        "failures": list(FAIL),
        "error": error,
    }
    with open(os.path.join(report_dir, "e2e_test_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    try:
        run_test()
    except BaseException as exc:
        write_report("failed", f"{type(exc).__name__}: {exc}")
        raise
    else:
        write_report("passed")
