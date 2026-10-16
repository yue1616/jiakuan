#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在当前电脑/网络上复测代理，生成两轮连续通过且速度达标的 v2rayN 订阅。

该工具复用本仓库 scripts/main_v2.py 的 URI 解析与 sing-box 配置构建。
它刻意不做出口地域分类：只检查当前网络能否稳定连接、目标站点能否返回响应，以及实际下载速度。
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    import main_v2 as mv
except Exception as exc:
    print(f"[错误] 导入 scripts/main_v2.py 失败：{exc}")
    print("请先在项目根目录执行：python -m pip install -r scripts/requirements.txt")
    raise

DEFAULT_URL = "https://cdn.jsdelivr.net/gh/yue1616/jiakuan@main/output/v2ray.txt"
LIVENESS_TARGETS = [
    ("https://www.google.com/generate_204", {204}),
    ("https://www.gstatic.com/generate_204", {204}),
    ("https://www.cloudflare.com/cdn-cgi/trace", {200}),
]
SPEED_TARGETS = [
    "https://speed.cloudflare.com/__down?bytes=2500000",
    "https://cachefly.cachefly.net/10mb.test",
]


def find_singbox(explicit: str | None) -> Path | None:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    if os.environ.get("SINGBOX_EXE"):
        candidates.append(Path(os.environ["SINGBOX_EXE"]).expanduser())
    candidates.extend([
        REPO_DIR / "runtime" / "sing-box.exe",
        REPO_DIR / "runtime" / "sing-box",
        REPO_DIR / "sing-box.exe",
        Path.cwd() / "sing-box.exe",
        Path.cwd() / "bin" / "sing_box" / "sing-box.exe",
        Path.cwd() / "bin" / "sing-box" / "sing-box.exe",
    ])
    for path in candidates:
        if path.is_file() and path.stat().st_size > 1024:
            return path.resolve()
    return None


def read_subscription(input_path: str | None, input_url: str | None) -> tuple[str, str]:
    if input_path:
        path = Path(input_path).expanduser()
        return path.read_text(encoding="utf-8-sig", errors="ignore"), str(path.resolve())
    url = input_url or DEFAULT_URL
    print(f"[*] 下载订阅：{url}")
    response = mv.DIRECT_SESSION.get(url, timeout=30, headers={"Accept": "*/*"})
    response.raise_for_status()
    return response.text, url


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def probe_one(item: tuple, speed_floor: int, max_latency: int, startup_timeout: float = 5.0) -> dict:
    raw, outbound, server, port, proto = item
    port_local = free_port()
    cfg_path = Path(mv.RUNTIME_DIR) / f"local_probe_{uuid.uuid4().hex[:10]}.json"
    process = None
    err_text = ""
    try:
        cfg = mv.build_test_config(outbound, port_local)
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg_path.write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        exe = mv.SINGBOX_BIN + (".exe" if os.name == "nt" else "")

        check = subprocess.run([exe, "check", "-c", str(cfg_path)], capture_output=True, text=True, timeout=10)
        if check.returncode != 0:
            return {"ok": False, "reason": "sing-box 配置校验失败", "server": server, "port": port, "proto": proto}

        process = subprocess.Popen(
            [exe, "run", "-c", str(cfg_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            creationflags=(subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0),
        )
        deadline = time.monotonic() + startup_timeout
        ready = False
        while time.monotonic() < deadline:
            if process.poll() is not None:
                try:
                    err_text = (process.stderr.read() or b"").decode("utf-8", errors="replace")[:500]
                except Exception:
                    pass
                break
            try:
                with socket.create_connection(("127.0.0.1", port_local), timeout=0.25):
                    ready = True
                    break
            except OSError:
                time.sleep(0.1)
        if not ready:
            return {"ok": False, "reason": "sing-box 未启动或 SOCKS 未就绪", "detail": err_text,
                    "server": server, "port": port, "proto": proto}

        proxies = {"http": f"socks5h://127.0.0.1:{port_local}",
                   "https": f"socks5h://127.0.0.1:{port_local}"}
        successes = []
        for url, accepted_codes in LIVENESS_TARGETS:
            started = time.monotonic()
            try:
                response = mv.PROBE_SESSION.get(
                    url, proxies=proxies, timeout=(3.0, 4.0), allow_redirects=False, verify=True
                )
                elapsed_ms = int((time.monotonic() - started) * 1000)
                if response.status_code in accepted_codes:
                    successes.append({"url": url, "latency_ms": elapsed_ms})
            except Exception:
                continue
            if len(successes) >= 2:
                break
        if len(successes) < 2:
            return {"ok": False, "reason": "独立 HTTPS 探测少于 2 个成功", "server": server,
                    "port": port, "proto": proto, "successful_targets": len(successes)}

        latency = int(sum(x["latency_ms"] for x in successes) / len(successes))
        if latency > max_latency:
            return {"ok": False, "reason": "延迟超过门槛", "server": server, "port": port,
                    "proto": proto, "latency_ms": latency}

        speed = 0
        for speed_url in SPEED_TARGETS:
            start = time.monotonic()
            downloaded = 0
            try:
                with mv.PROBE_SESSION.get(speed_url, proxies=proxies, timeout=(3.0, 2.5),
                                          stream=True, allow_redirects=True, verify=True) as response:
                    if response.status_code == 200:
                        for chunk in response.iter_content(chunk_size=65536):
                            if chunk:
                                downloaded += len(chunk)
                            elapsed = time.monotonic() - start
                            if elapsed >= 5.0 or downloaded >= 2_500_000:
                                break
                elapsed = max(time.monotonic() - start, 0.001)
                if downloaded:
                    speed = int(downloaded / elapsed)
                    break
            except Exception:
                continue
        if speed < speed_floor:
            return {"ok": False, "reason": "下载速度低于门槛或测速无数据", "server": server,
                    "port": port, "proto": proto, "latency_ms": latency, "speed_bytes_per_s": speed}
        return {"ok": True, "reason": "通过", "server": server, "port": port, "proto": proto,
                "latency_ms": latency, "speed_bytes_per_s": speed, "raw": raw}
    except subprocess.TimeoutExpired:
        return {"ok": False, "reason": "sing-box 检查超时", "server": server, "port": port, "proto": proto}
    except Exception as exc:
        return {"ok": False, "reason": f"检测异常：{type(exc).__name__}", "server": server, "port": port, "proto": proto}
    finally:
        if process and process.poll() is None:
            process.kill()
            try:
                process.wait(timeout=2)
            except Exception:
                pass
        if process and process.stderr:
            try:
                process.stderr.close()
            except Exception:
                pass
        try:
            cfg_path.unlink(missing_ok=True)
        except OSError:
            pass


def run_batch(items: list[tuple], speed_floor: int, max_latency: int, workers: int, label: str) -> list[tuple[tuple, dict]]:
    good: list[tuple[tuple, dict]] = []
    reasons: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(probe_one, item, speed_floor, max_latency): item for item in items}
        for idx, future in enumerate(as_completed(futures), 1):
            item = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"ok": False, "reason": f"执行异常：{type(exc).__name__}"}
            reason = result.get("reason", "未知")
            reasons[reason] = reasons.get(reason, 0) + 1
            if result.get("ok"):
                good.append((item, result))
            if idx % 25 == 0 or idx == len(items):
                print(f"[{label}] {idx}/{len(items)}，当前通过 {len(good)}")
    print(f"[{label}] 失败原因统计：" + "；".join(f"{k}={v}" for k, v in sorted(reasons.items(), key=lambda x: -x[1])))
    return good


def main() -> int:
    parser = argparse.ArgumentParser(description="在当前网络对 jiakuan 节点做严格本地复测")
    parser.add_argument("--input", help="本地 output/v2ray.txt 文件；省略则下载在线订阅")
    parser.add_argument("--url", default=None, help="在线订阅 URL")
    parser.add_argument("--sing-box", default=None, help="sing-box.exe 完整路径")
    parser.add_argument("--workers", type=int, default=4, help="并发数，默认 4")
    parser.add_argument("--min-speed", type=int, default=250_000, help="最低速度字节/秒，默认 250000（约 2 Mbps）")
    parser.add_argument("--max-latency", type=int, default=700, help="最大 HTTPS 探测耗时毫秒，默认 700")
    parser.add_argument("--out-dir", default=str(REPO_DIR / "output" / "local-verified"), help="输出目录")
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 12:
        parser.error("--workers 必须介于 1 到 12")
    if args.min_speed < 70_000:
        parser.error("--min-speed 不建议低于项目原本的 70000 B/s")

    sb = find_singbox(args.sing_box)
    if not sb:
        print("[错误] 找不到 sing-box。请使用 --sing-box 指向 sing-box.exe 完整路径。")
        return 2
    mv.SINGBOX_BIN = str(sb.with_suffix("") if sb.suffix.lower() == ".exe" else sb)
    # 明确测试本机到节点的直连路径，不套用 CI 的 FRONT_PROXY。
    os.environ.pop("FRONT_PROXY", None)
    mv.RUNTIME_DIR = str(REPO_DIR / "runtime")
    Path(mv.RUNTIME_DIR).mkdir(parents=True, exist_ok=True)

    try:
        text, source = read_subscription(args.input, args.url)
    except Exception as exc:
        print(f"[错误] 读取订阅失败：{type(exc).__name__}: {exc}")
        print("可以先在浏览器下载 v2ray.txt，再使用 --input 指定本地文件。")
        return 3

    uris = sorted(mv.extract_nodes_from_text(text))
    items = []
    parse_fail = 0
    incompatible = 0
    seen = set()
    for uri in uris:
        parsed = mv.parse_node_uri(uri)
        if not parsed:
            parse_fail += 1
            continue
        outbound, server, port, proto = parsed
        if not mv.outbound_to_v2ray_link(outbound, "local-check"):
            incompatible += 1
            continue
        key = mv.node_dedup_key(outbound, server, int(port), proto)
        if key in seen:
            continue
        seen.add(key)
        items.append((uri, outbound, server, int(port), proto))
    if not items:
        print("[错误] 没有可测试的节点；请确认订阅内容与项目 scripts/main_v2.py 匹配。")
        return 4

    print("==== 当前网络严格复测 ====")
    print(f"订阅：{source}")
    print(f"sing-box：{sb}")
    print(f"原始链接：{len(uris)} | 解析失败：{parse_fail} | v2rayN 兼容过滤：{incompatible} | 去重待测：{len(items)}")
    print(f"门槛：两轮通过；每轮至少 2 个独立 HTTPS 探测成功；下载 ≥ {args.min_speed:,} B/s；探测 ≤ {args.max_latency} ms")

    round1 = run_batch(items, args.min_speed, args.max_latency, args.workers, "第一轮")
    if not round1:
        print("[结果] 当前网络下无节点通过严格测试；没有生成空订阅。")
        return 5
    round2 = run_batch([item for item, _ in round1], args.min_speed, args.max_latency, args.workers, "稳定复测")
    stable_uris = {item[0] for item, _ in round2}
    stable = [(item, info) for item, info in round1 if item[0] in stable_uris]
    stable.sort(key=lambda pair: (pair[1].get("latency_ms", 999999), -pair[1].get("speed_bytes_per_s", 0)))

    links = []
    report_nodes = []
    for idx, (item, info) in enumerate(stable, 1):
        _, outbound, server, port, proto = item
        link = mv.outbound_to_v2ray_link(outbound, f"本地可用-{idx:03d}-{proto}")
        if not link:
            continue
        links.append(link)
        report_nodes.append({"name": f"本地可用-{idx:03d}", "protocol": proto, "server": server, "port": port,
                             "https_latency_ms": info.get("latency_ms"),
                             "download_bytes_per_s": info.get("speed_bytes_per_s")})
    if not links:
        print("[结果] 没有兼容的节点可输出，未生成空订阅。")
        return 6

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    plain = "\n".join(links) + "\n"
    (out_dir / "v2ray-local-tested.txt").write_text(base64.b64encode(plain.encode("utf-8")).decode("ascii"), encoding="utf-8")
    (out_dir / "v2ray-local-tested-links.txt").write_text(plain, encoding="utf-8")
    report = {
        "source": source,
        "tested_from_current_machine_network": True,
        "criteria": {"minimum_successful_https_targets": 2, "required_successful_rounds": 2,
                     "minimum_speed_bytes_per_s": args.min_speed, "maximum_probe_latency_ms": args.max_latency},
        "counts": {"raw_uris": len(uris), "parse_failed": parse_fail, "compatibility_filtered": incompatible,
                   "unique_tested": len(items), "round1_pass": len(round1), "stable_pass": len(links)},
        "nodes": report_nodes,
    }
    (out_dir / "local-test-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n==== 最终结果 ====")
    print(f"第一轮通过：{len(round1)} / {len(items)}")
    print(f"两轮稳定通过：{len(links)}")
    print(f"订阅文件：{out_dir / 'v2ray-local-tested.txt'}")
    print(f"明文链接：{out_dir / 'v2ray-local-tested-links.txt'}")
    print(f"检测报告：{out_dir / 'local-test-report.json'}")
    print("请单独导入本地复测订阅，不要覆盖 GitHub 原始总订阅。通过情况只代表当前网络与本次测试时间。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
