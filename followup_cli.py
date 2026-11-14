# -*- coding: utf-8 -*-
"""
追问引擎 · 命令行工具

用途
────
给冷咖啡全自动破甲的追问解析引擎做手动检查，不依赖 GUI。

用法
────
  python followup_cli.py status            看当前状态（根主题 / 已覆盖 / 最近几轮）
  python followup_cli.py reset [根主题]     重置会话
  python followup_cli.py test 句子1 句子2   按顺序跑一串输入，打印每轮判定
  python followup_cli.py dry 句子           只判定这一句，不写状态
"""

import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import followup_engine as fe


def _cfg():
    try:
        with io.open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"api_url": "http://127.0.0.1:17801/chat/completions",
                "model": "deepseek-flash", "api_key": ""}


def cmd_status():
    s = fe.load_state()
    print("根主题    : %s" % (s.get("root") or "（空）"))
    print("已覆盖    : %s" % ("、".join(s.get("covered") or []) or "（无）"))
    print("更新时间  : %s" % (s.get("updated") or 0))
    turns = s.get("turns") or []
    if not turns:
        print("轮次      : （无）")
        return
    print("最近轮次  :")
    for t in turns[-8:]:
        print("  [%s] %-8s %-6s %-14s %s"
              % (t.get("kind", "")[:8], t.get("by", ""),
                 (t.get("subtype") or "-")[:14], (t.get("ask") or "")[:22],
                 t.get("topic", "")))


def cmd_reset(root=""):
    fe.reset(root)
    print("已重置。根主题 = %s" % (root or "（空）"))


def cmd_test(sentences):
    cfg = _cfg()
    print("配置: %s  model=%s\n" % (cfg.get("api_url"), cfg.get("model")))
    for q in sentences:
        r, s = fe.resolve(q, cfg)
        print("输入   : %s" % q)
        print("  判定   : %s（第 %s 层）" % (r["kind"], r["by"]))
        print("  根主题 : %s" % s.get("root"))
        if r.get("subtype"):
            print("  子类型 : %s" % r["subtype"])
        if r.get("avoid"):
            print("  不重复 : %s" % "、".join(r["avoid"]))
        print("  送上游 :")
        for ln in (r.get("prompt") or "").split("\n"):
            if ln.strip():
                print("    %s" % ln)
        print()


def cmd_dry(sentence):
    """只判定，不写状态。用于验证某句话会被怎么归类。"""
    cfg = _cfg()
    s = fe.load_state()
    root = s.get("root", "")
    covered = list(s.get("covered") or [])
    a = fe._clean(sentence)
    r = fe._l1(a, root) or fe._l2(a, root) or fe._l3(cfg, a, root, covered)
    if not r:
        r = {"kind": "new_topic", "by": "default", "subtype": "", "qualifier": "", "avoid": []}
    print("输入   : %s" % a)
    print("当前根 : %s" % (root or "（空）"))
    print("判定   : %s（第 %s 层）" % (r["kind"], r["by"]))
    print("子类型 : %s" % (r.get("subtype") or "-"))
    print("修饰   : %s" % (r.get("qualifier") or "-"))
    print("（未写状态）")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd = args[0]
    rest = args[1:]
    if cmd == "status":
        cmd_status()
    elif cmd == "reset":
        cmd_reset(rest[0] if rest else "")
    elif cmd == "test":
        if not rest:
            print("用法: followup_cli.py test 句子1 句子2 …")
            return 2
        cmd_test(rest)
    elif cmd == "dry":
        if not rest:
            print("用法: followup_cli.py dry 句子")
            return 2
        cmd_dry(" ".join(rest))
    else:
        print("未知命令: %s" % cmd)
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
