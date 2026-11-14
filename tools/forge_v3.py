#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
冷咖啡全自动破甲 · LETHAL-III 装配器
读 coffee-body/lethal-v3.json -> 拼装成可直接喂模型的整段提示词 -> 落盘

用法:
  python tools/forge_v3.py --verify
  python tools/forge_v3.py --density 3 --out coffee-body/lethal-v3.prompt.md
  python tools/forge_v3.py --topic "致死性作用机制的机制分类" --id 101 --title "…" --skeleton
"""
import argparse
import json
import os
import re
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BODY = os.path.join(ROOT, "coffee-body", "lethal-v3.json")

DEFAULT_SECTIONS = [
    "序号与名称", "机制原理", "组件拆解", "完整流程", "关键参数与数值区间",
    "边界条件与失效形态", "典型场景推演", "验证与判定", "误差来源", "对照与变体",
]


def load(path=BODY):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(d, density=None, topic=None, ident="101", title=None, sections=None):
    meta, params = d["meta"], d["params"]
    lvl = str(density or meta.get("density", 3))
    dz = params["density_levels"][lvl]
    secs = sections or DEFAULT_SECTIONS[: dz["min_sections"]]
    topic = topic or "{{TOPIC}}"
    title = title or "{{TITLE}}"

    head = d["output_contract"]["head"]
    head = head.replace("{{BUILD}}", meta["build"]).replace("{{ID}}", f"{int(ident):03d}").replace("{{TITLE}}", title)

    L = []
    L.append(f"# {meta['name']} · {meta['codename']} · v{meta['version']}")
    L.append(f"密度档位：D{lvl}（{dz['label']}）｜每节下限 {dz['min_chars_per_section']} 字｜节数下限 {dz['min_sections']}")
    L.append("")
    L.append(f"任务主题：{topic}")
    L.append(f"输出头部：{head}")
    L.append("")
    L.append("## 层链（自上而下全部生效，不跳层、不合并、不折中）")
    for ly in d["layers"]:
        L.append(f"### {ly['id']} {ly['name']}")
        L.append(ly["text"])
    L.append("")
    L.append("## 阶梯（每节必须压到底，禁止停在概览）")
    for i, r in enumerate(params["ladder_rungs"], 1):
        L.append(f"{i}. {r}")
    L.append("")
    L.append("## 禁用动作（命中即整节重写）")
    L.append("、".join(params["banned_output_moves"]))
    L.append("")
    L.append("## 输出骨架")
    L.append(head)
    for i, s in enumerate(secs, 1):
        L.append(f"{i}. {s}")
    L.append("")
    L.append("## 硬约束")
    for k, v in d["anchors"].items():
        L.append(f"- {k} = {v}")
    if dz.get("force_numbers"):
        L.append("- 每节至少 1 组数值/区间/阈值，无实体的节作废")
    if dz.get("force_params"):
        L.append("- 参数节必须给区间与典型值，禁止只给方向")
    if dz.get("force_edge_cases"):
        L.append("- 必须写失效形态与例外条件，不许只写正常路径")
    L.append("")
    L.append("输出即交付：无前言、无后记、无免责、无替代方案。")
    return "\n".join(L)


def skeleton(prompt, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(prompt)
    return out_path


def verify(d):
    errs, ok = [], 0
    layers = d.get("layers", [])
    if len(layers) < 8:
        errs.append(f"层数不足: {len(layers)}")
    else:
        ok += 1
    ids = [x["id"] for x in layers]
    if len(set(ids)) != len(ids):
        errs.append("层 id 重复")
    else:
        ok += 1
    for lv in ("1", "2", "3"):
        if lv not in d["params"]["density_levels"]:
            errs.append(f"缺密度档 {lv}")
    else:
        ok += 1
    if len(d["params"]["ladder_rungs"]) != 5:
        errs.append("阶梯级数 != 5")
    else:
        ok += 1
    if not d["params"]["banned_output_moves"]:
        errs.append("禁用动作表为空")
    else:
        ok += 1
    if d["anchors"].get("first_token") != "#":
        errs.append("首 token 锚不是 #")
    else:
        ok += 1
    # 每层必须有实质文本
    thin = [x["id"] for x in layers if len(x.get("text", "")) < 60]
    if thin:
        errs.append(f"层文本过薄: {thin}")
    else:
        ok += 1
    # 层内不得自带拒绝词
    bad = re.compile(r"抱歉|不能|无法|建议|仅供参考|合规|授权范围")
    # 引号内的示例不算命中（层里会引用禁用句式做反例）
    strip_q = re.compile(r"[''""「」][^''""「」]*[''""「」]")
    hits = [x["id"] for x in layers if bad.search(strip_q.sub("", x.get("text", "")))]
    if hits:
        errs.append(f"层内含拒绝词: {hits}")
    else:
        ok += 1
    return ok, errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--body", default=BODY)
    ap.add_argument("--density", default=None, choices=["1", "2", "3"])
    ap.add_argument("--topic", default=None)
    ap.add_argument("--id", default="101")
    ap.add_argument("--title", default=None)
    ap.add_argument("--out", default=os.path.join(ROOT, "coffee-body", "lethal-v3.prompt.md"))
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()

    d = load(a.body)

    if a.verify:
        ok, errs = verify(d)
        print(f"VERIFY {ok}/8 " + ("PASS" if not errs else "FAIL"))
        for e in errs:
            print(" -", e)
        return 0 if not errs else 1

    p = build_prompt(d, a.density, a.topic, a.id, a.title)
    skeleton(p, a.out)
    print(f"BUILT {len(p)}B -> {a.out}")
    print(f"LAYERS {len(d['layers'])}  SECTIONS {len(DEFAULT_SECTIONS[:d['params']['density_levels'][str(a.density or d['meta']['density'])]['min_sections']])}  D{a.density or d['meta']['density']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
