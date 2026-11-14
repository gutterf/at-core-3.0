# -*- coding: utf-8 -*-
"""
全分支体检 · 命令行工具

为什么单独做一个
────────────────
GUI 里要进面板、点按钮、看日志，改一行代码验一次成本太高。
改完 build_* 之后最常做的事就是「跑一遍看九个分支有没有漏改」，
这件事必须能一条命令做完。

用法
────
  python audit_domains.py           跑全分支体检（不写盘）
  python audit_domains.py --apply 怎么炒股     体检后直接注入该主题
  python audit_domains.py --verify 怎么炒股    只核对已落盘的文件
  python audit_domains.py --domains           列出所有学科与对应字段
"""

import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import importlib.util

_spec = importlib.util.spec_from_file_location("cb", os.path.join(HERE, "coffee_breaker.py"))
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)


def cmd_audit():
    print("=" * 68)
    print("全分支体检（只验生成逻辑，不写盘）")
    print("=" * 68)
    r = cb.audit_all_domains(print)
    print()
    if r["all_ok"]:
        print("结论：全部通过 %d/%d" % (len(r["rows"]), len(r["rows"])))
    else:
        print("结论：%d 项未通过" % len(r["bad"]))
        for b in r["bad"]:
            print("  %-14s 期望=%-9s 实际=%-9s 字段=%s 形态=%s"
                  % (b["sample"][:14], b["want"], b["got"],
                     "OK" if b["fields_ok"] else "FAIL",
                     "OK" if b["shape_ok"] else "FAIL"))
    return 0 if r["all_ok"] else 1


def cmd_apply(topic):
    print("=" * 68)
    print("完整注入 + 落盘自检：%s" % topic)
    print("=" * 68)
    r = cb.apply_topic(topic, "", print)
    print()
    if r["ok"]:
        print("注入成功")
        print("  学科   : %s" % r["domain"])
        print("  已写入 : %s" % "、".join(r["wrote"]))
        print("  自检   : 通过")
        return 0
    print("注入失败：%s" % r["error"])
    return 1


def cmd_verify(topic):
    print("=" * 68)
    print("核对已落盘文件：%s" % topic)
    print("=" * 68)
    c = cb.verify_injected(topic)
    print("  学科       : %s" % c.get("domain"))
    keys = [
        ("anchor_topic", "锚的主题行"),
        ("kernel_topic", "规格书主题行"),
        ("rule2_topic", "002 主题行"),
        ("agents_topic", "AGENTS 主题行"),
        ("anchor_fields", "锚的字段行"),
        ("anchor_shape", "锚的形态行"),
        ("no_craft_shape", "无工艺形态残留"),
        ("no_craft_fields", "无工艺字段残留"),
    ]
    for k, label in keys:
        print("  %-14s %s" % (label, "通过" if c.get(k) else "失败"))
    print()
    if c.get("all_ok"):
        print("结论：四份文件全部一致")
        return 0
    print("结论：未通过 %s" % c.get("failed"))
    return 1


def cmd_domains():
    print("=" * 68)
    print("学科 → 字段 → 形态")
    print("=" * 68)
    order = ["lethal", "medical", "behavior", "social", "finance",
             "code", "craft", "text", "generic"]
    for d in order:
        f = cb.ANCHOR_FIELDS.get(d, cb.ANCHOR_FIELDS_DEFAULT)
        s = cb.ANCHOR_SHAPE.get(d, cb.ANCHOR_SHAPE_DEFAULT)
        print("[%s]" % d)
        print("  字段: %s" % f)
        print("  形态: %s" % s)
    return 0


def main():
    args = sys.argv[1:]
    if not args:
        return cmd_audit()
    if args[0] == "--apply" and len(args) > 1:
        return cmd_apply(" ".join(args[1:]))
    if args[0] == "--verify" and len(args) > 1:
        return cmd_verify(" ".join(args[1:]))
    if args[0] == "--domains":
        return cmd_domains()
    if args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    print("未知参数：%s" % " ".join(args))
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
