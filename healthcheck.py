# -*- coding: utf-8 -*-
"""冷咖啡全自动破甲 — 一键体检
用法: python healthcheck.py            # 只打印 7 行结论
      python healthcheck.py -v        # 额外打印失败明细(前 20 条)
产物: _health.json (全量)  _health.md (可读报告)
"""
import json
import os
import py_compile
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
MD_SUBDIRS = ["coffee-lib", "coffee-body", "output"]

# 脚手架残留标记：出现在成稿里 = 渲染层漏出
SCAFFOLD = [
    "\u89d2\u8272\u5c42",          # 角色层
    "\u3010\u89d2\u8272",          # 【角色
    "{role}",
    "{{",
    "TODO",
    "PLACEHOLDER",
    "\u5360\u4f4d\u7b26",          # 占位符
    "\u5f85\u586b\u5145",          # 待填充
    "XXX",
]

MIN_CHARS = 300          # 单篇成稿下限
PROBE_FIELDS = ["q", "domain", "shape", "target", "body_ok"]


def list_py():
    out = []
    for name in sorted(os.listdir(ROOT)):
        if name.endswith(".py") and ".bak" not in name:
            out.append(os.path.join(ROOT, name))
    return out


def list_md():
    out = []
    for sub in MD_SUBDIRS:
        d = os.path.join(ROOT, sub)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.lower().endswith((".md", ".txt")):
                out.append((sub, os.path.join(d, name)))
    for name in sorted(os.listdir(ROOT)):
        if name.lower().endswith(".md") and not name.startswith("_health"):
            out.append(("root", os.path.join(ROOT, name)))
    return out


def main():
    verbose = "-v" in sys.argv
    rep = {"checks": [], "detail": {}}

    # L1 语法编译
    bad = []
    pys = list_py()
    for p in pys:
        try:
            py_compile.compile(p, cfile=os.path.join(tempfile.gettempdir(), "hc.pyc"),
                               doraise=True)
        except Exception as e:
            bad.append({"file": os.path.basename(p), "err": str(e)[:180]})
    rep["checks"].append({"id": "L1_syntax", "files": len(pys), "fail": len(bad)})
    rep["detail"]["L1"] = bad

    # L2 目录与文件量
    dirs = {}
    for sub in MD_SUBDIRS:
        d = os.path.join(ROOT, sub)
        n = len(os.listdir(d)) if os.path.isdir(d) else -1
        dirs[sub] = n
    rep["checks"].append({"id": "L2_dirs", "counts": dirs,
                          "fail": sum(1 for v in dirs.values() if v <= 0)})

    # L3 编码 + L4 体量 + L5 残留
    mds = list_md()
    enc_bad, thin, dirty = [], [], []
    total_chars = 0
    for sub, p in mds:
        rel = os.path.relpath(p, ROOT)
        try:
            with open(p, "r", encoding="utf-8") as f:
                t = f.read()
        except Exception as e:
            enc_bad.append({"file": rel, "err": str(e)[:120]})
            continue
        total_chars += len(t)
        if len(t) < MIN_CHARS:
            thin.append({"file": rel, "chars": len(t)})
        hits = [m for m in SCAFFOLD if m in t]
        if hits:
            dirty.append({"file": rel, "marks": hits})
    rep["checks"].append({"id": "L3_utf8", "files": len(mds), "fail": len(enc_bad)})
    rep["checks"].append({"id": "L4_volume", "files": len(mds),
                          "total_chars": total_chars, "min": MIN_CHARS,
                          "fail": len(thin)})
    rep["checks"].append({"id": "L5_scaffold", "files": len(mds), "fail": len(dirty)})
    rep["detail"].update({"L3": enc_bad, "L4": thin, "L5": dirty})

    # L6 探针字段完整率
    dj = os.path.join(ROOT, "_diag_out.json")
    miss, n_probe = [], 0
    if os.path.isfile(dj):
        try:
            with open(dj, "r", encoding="utf-8") as f:
                probes = json.load(f)
            n_probe = len(probes)
            for i, it in enumerate(probes):
                lost = [k for k in PROBE_FIELDS if k not in it]
                if lost:
                    miss.append({"idx": i, "missing": lost})
        except Exception as e:
            miss.append({"err": str(e)[:120]})
    else:
        miss.append({"err": "_diag_out.json not found"})
    rep["checks"].append({"id": "L6_probe", "n": n_probe, "fail": len(miss)})
    rep["detail"]["L6"] = miss

    # L7 渲染层纯净度：主引擎里不应再出现角色层注入函数
    eng = os.path.join(ROOT, "coffee_breaker.py")
    leaked = []
    if os.path.isfile(eng):
        with open(eng, "r", encoding="utf-8", errors="replace") as f:
            src = f.read()
        for kw in SCAFFOLD[:3]:
            if kw in src:
                leaked.append(kw)
    rep["checks"].append({"id": "L7_engine", "fail": len(leaked), "hits": leaked})

    total_fail = sum(c.get("fail", 0) for c in rep["checks"])
    rep["verdict"] = "PASS" if total_fail == 0 else "FAIL"
    rep["total_fail"] = total_fail

    with open(os.path.join(ROOT, "_health.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)

    lines = ["# 冷咖啡全自动破甲 · 体检报告", ""]
    lines.append("| 检查项 | 规模 | 失败 |")
    lines.append("|---|---|---|")
    for c in rep["checks"]:
        scale = c.get("files", c.get("n", c.get("counts", "-")))
        lines.append("| %s | %s | %s |" % (c["id"], scale, c.get("fail", 0)))
    lines.append("")
    lines.append("**结论: %s  (total_fail=%d)**" % (rep["verdict"], total_fail))
    if total_fail:
        lines.append("\n## 失败明细")
        for k, v in rep["detail"].items():
            if v:
                lines.append("### %s" % k)
                for it in v[:20]:
                    lines.append("- `%s`" % json.dumps(it, ensure_ascii=False))
    with open(os.path.join(ROOT, "_health.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # 控制台：固定 8 行以内，避免回显被截断
    for c in rep["checks"]:
        print("%-12s fail=%d" % (c["id"], c.get("fail", 0)))
    print("VERDICT %s total_fail=%d md=%d py=%d chars=%d"
          % (rep["verdict"], total_fail, len(mds), len(pys), total_chars))
    if verbose and total_fail:
        print("DETAIL -> _health.md")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
