# 应用 jiakuan 严格池 / 候选池第一阶段补丁

1. 先备份本机 `D:\jiakuan`（不要删除已有备份）。
2. 将这个 ZIP 解压到 `D:\jiakuan`，保留 ZIP 内的目录结构并允许覆盖同名源文件。
3. 这次仅需覆盖：
   - `scripts\main_v2.py`
   - `scripts\test_parsers.py`
   - `.github\workflows\update.yml`
   并新增 `AIMILI_PHASE1_NOTES.md`、`APPLY_PATCH.md`。
4. 先在 PowerShell 中运行：

```powershell
py -m py_compile D:\jiakuan\scripts\main_v2.py D:\jiakuan\scripts\test_parsers.py
```

5. 把这几个文件提交并推送到 GitHub 的 `main` 分支；远程更新后，再从 Actions 手动运行 `Update Subscriptions`。
6. 确认新的 Actions 成功后，主订阅仍使用原地址；候选池单独位于 `output/candidates/`。

本补丁不包含 `output/` 或 `runtime/`，不会覆盖现有节点文件、数据库或 sing-box 程序。
