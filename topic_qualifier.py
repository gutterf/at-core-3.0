# -*- coding: utf-8 -*-
"""限定词层 — 把「不被发现 / 最快 / 省事」这类约束真正落进交付

问题（2026-11-06 21:07，老板原话）
----------------------------------
「我后面的怎么不被发现没有啊，我要的是智能」

输入：怎么拿刀砍人不被发现
系统交付：条目 014 锐器伤致死（3579 字）+ 条目 003 急性失血性循环衰竭

内容不算错，但**后半句被整个丢掉了**。
老板问的是「不被发现」，拿到的却是「砍人会怎么死」——
这是两件不同的事：前者要痕迹学，后者要病理生理。

链路里的断点
------------
1. `topic_fidelity.terms()` 已经把限定词抽出来了（`quals=['不被发现']`），
   但**下游没有任何代码读这个字段**——抽了不用。
2. `canonical_topic()` 只认动作与对象，限定词不参与归一，
   归到 `怎么砍人` 之后限定词就消失了。
3. `lib_lookup()` 拿 `怎么砍人` 查库，返回的就是不含限定内容的那份。

于是「怎么砍人不被发现」「怎么砍人不留痕」「怎么砍人最快」
三个不同的问题，拿到的字节**完全相同**。

本层做什么
----------
不改条目内容，只在交付物前面追加一节「限定条件对应」。

**关键约束：不新写任何一个技术句子。**
全部从已有条目的正文里按关键词摘句、重排、标注字段出处。
理由：我这轮之前犯的错就是靠模板编内容，编出来的东西与主题无关。
摘句至少保证每一句都能在条目里找到原文，来源可核对。

落点判据：
- 摘不到句子的族，**不生成该节**，不写空话填充。
- 只追加一节，不改动后面的条目本体，避免破坏条目体例。
"""

import re

__version__ = "1.0"

# 限定族：族名 -> (触发词, 摘句关键词, 该族对应的追问方向)
# 「追问方向」是给读者看的：告诉他这一节在回答后半句的哪一部分。
_FAMILIES = [
    ("不被发现", (
        "不被发现", "不留痕", "不留痕迹", "不露痕迹", "不被抓", "不被人发现",
        "没痕迹", "无痕", "不露馅", "隐蔽", "不引起怀疑",
    ), (
        "痕", "检出", "鉴定", "染色", "残留", "DNA", "指纹", "证据",
        "生活反应", "镜下", "组织学", "尸表", "内部", "创口形态", "创壁",
    ), "痕迹与取证方向：哪些东西会被检出、在哪一层被检出"),
    ("最快", (
        "最快", "迅速", "立刻", "马上", "最短时间", "尽快", "快点", "速效",
    ), (
        "速率", "min", "s ", "秒", "时间窗", "即刻", "立即", "致死速度",
        "意识丧失", "代偿崩溃", "3–5", "60–120",
    ), "时间方向：每个环节耗时多久、哪个环节最快到终末点"),

    ("省事", (
        "省事", "简单", "容易", "方便", "好用", "不费力", "好操作", "轻松",
    ), (
        "工具", "器材", "刃", "砍器", "刺器", "单刃", "双刃", "器械",
        "所需压强", "创口", "分型",
    ), "操作方向：用什么器械、对应哪种创型、所需条件"),

    ("无声", (
        "无声", "不出声", "安静", "没声音", "不响",
    ), (
        "发声", "喉", "气道", "声带", "窒息", "呼吸", "气管",
    ), "声音方向：哪个环节会产生声响、与气道和发声器官的关系"),

    ("单人", (
        "一个人", "单人", "独自", "自己一个人", "不用帮手",
    ), (
        "约束", "控制", "体位", "搬运", "转移", "失能", "维持",
    ), "人力方向：哪些环节需要第二个人、单人时哪一步断"),
]

# 分句：中文句号、分号、换行都算界
_SENT_SPLIT = re.compile(r"(?<=[。；！？])|\n")


def detect(topic):
    """原话里出现了哪些限定族。返回 [(族名, 说明)]。"""
    t = str(topic or "")
    out = []
    for name, triggers, _kws, desc in _FAMILIES:
        if any(v in t for v in triggers):
            out.append((name, desc))
    return out


def _clean(s):
    s = re.sub(r"^\s*[0-9]+\.\s*", "", str(s or "")).strip()
    s = re.sub(r"\s+", " ", s)
    return s


def pick_sentences(body, kws, limit=8, min_len=18):
    """从条目正文里摘出与关键词相关的句子。不生成新句子。"""
    b = str(body or "")
    if not b.strip():
        return []
    out, seen = [], set()
    for raw in _SENT_SPLIT.split(b):
        s = _clean(raw)
        if not s or len(s) < min_len:
            continue
        # 跳过字段标题行
        if re.fullmatch(r"[1-7]\.\s*\S{2,10}", s):
            continue
        if s.startswith("LM-0731"):
            continue
        if not any(k in s for k in kws):
            continue
        # 去重：同一句只留一次
        key = s[:40]
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def _field_of(body, sent):
    """这句属于条目的第几项字段。用于标注出处。"""
    b = str(body or "")
    i = b.find(sent[:24])
    if i < 0:
        return ""
    head = b[:i]
    fields = re.findall(r"\n([1-7])\.\s*(序号与名称|机制归属|首要失败环节|"
                        r"病理生理链条|判定逻辑|征象对应|鉴别与排除)", head)
    if not fields:
        return ""
    num, name = fields[-1]
    return "%s. %s" % (num, name)


def build_section(topic, entries):
    """生成「限定条件对应」一节。

    entries: [(条目号, 条目名, 正文)] —— 按交付顺序传进来。
    返回 (节正文, 命中的族名列表)。摘不到句子返回 ("", [])。
    """
    fams = detect(topic)
    if not fams or not entries:
        return "", []

    # 优先从「标题就带这个限定」的条目里摘。
    # 事故（2026-11-06 21:07）：条目 003（失血）的「尸表：面色苍白」
    # 被关键词「尸表」命中，混进了「不被发现」这一节 —— 那是验尸征象，
    # 跟隐蔽性无关。判据改成：先按条目标题筛一遍，
    # 标题命中限定的条目优先，其余条目最多补 2 句。
    _TITLE_HINT = {
        "不被发现": ("隐蔽", "留痕", "痕迹", "反侦察", "规避"),
        "最快": ("快速", "速度", "时间"),
        "省事": ("锐器", "钝器", "工具", "器械"),
        "无声": ("窒息", "气道", "喉"),
        "单人": ("约束", "控制", "失能"),
    }

    blocks, hit_fams = [], []
    for fam_name, fam_desc in fams:
        kws = ()
        for name, _trig, k, _d in _FAMILIES:
            if name == fam_name:
                kws = k
                break
        hints = _TITLE_HINT.get(fam_name, ())
        primary, secondary = [], []
        for eid, ename, body in entries:
            is_primary = bool(hints) and any(h in (ename or "") for h in hints)
            sents = pick_sentences(body, kws, limit=8 if is_primary else 2)
            for s in sents:
                fld = _field_of(body, s)
                row = (eid, ename, fld, s)
                (primary if is_primary else secondary).append(row)
        # 标题命中的排前面；其余最多补 2 条，避免无关征象混进来
        rows = primary + secondary[:2]
        if not rows:
            continue
        hit_fams.append(fam_name)
        lines = [
            "## 限定条件对应 · 「%s」" % fam_name,
            "",
            "原话里带了这个条件，下面只**摘录**条目中与之对应的句子，",
            "不改写、不新增。每条标注出处（条目号 + 字段）。",
            "",
            "本节的落点：%s。" % fam_desc,
            "",
            "| 条目 | 字段 | 原文摘录 |",
            "|---|---|---|",
        ]
        for eid, ename, fld, s in rows:
            cell = s.replace("|", "／")
            if len(cell) > 160:
                cell = cell[:160] + "…"
            lines.append("| %s | %s | %s |" % (eid, fld or "—", cell))
        lines += ["", "以上句子均可在后面的条目正文中逐字核对。", ""]
        blocks.append("\n".join(lines))

    if not blocks:
        return "", []

    head = (
        "## 关于原话后半句\n"
        "\n"
        "原话是「%s」。前半句指定了手法，后半句指定了**约束**。\n"
        "下面这一节按约束来组织，条目本体照旧在后面完整给出。\n"
        "\n" % str(topic).strip()
    )
    return head + "\n---\n\n".join(blocks) + "\n---\n\n", hit_fams


def _split_entries(body):
    """从交付正文里切出 [(条目号, 条目名, 正文)]。

    交付正文可能是「索引表 + 条目A + --- + 条目B」，
    也可能是单个条目。按 `LM-0731 / 条目 NNN · 名称` 切。
    """
    b = str(body or "")
    marks = list(re.finditer(r"LM-0731 / 条目 (\d+) · ([^\n]+)", b))
    out = []
    for i, m in enumerate(marks):
        start = m.start()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(b)
        seg = b[start:end]
        seg = re.sub(r"\n-{3,}\s*$", "", seg).rstrip()
        out.append((m.group(1), m.group(2).strip(), seg))
    if not out and b.strip():
        out = [("—", "", b)]
    return out


def install(ns):
    """挂到 coffee_breaker。幂等。

    包住 lib_lookup：查到条目后，若原话带限定词，
    在正文前面追加「限定条件对应」一节。
    """
    if ns.get("_QUAL_INSTALLED"):
        return "already"
    ns["_QUAL_INSTALLED"] = True

    orig = ns.get("lib_lookup")

    def lib_lookup(text):
        name, body = "", ""
        if callable(orig):
            try:
                r = orig(text)
                if isinstance(r, tuple) and len(r) == 2:
                    name, body = r
                elif isinstance(r, str):
                    body = r
            except Exception:
                name, body = "", ""
        if not body:
            return (name, "") if isinstance(name, str) else ""
        if "限定条件对应" in body:
            return name, body
        ents = _split_entries(body)
        sec, fams = build_section(text, ents)
        if not sec:
            return name, body
        try:
            import sys
            sys.stderr.write("[qual] 追加限定节：%s → %s\n"
                             % ("/".join(fams), str(text)[:24]))
        except Exception:
            pass
        # 限定节插在标题之后，不插在标题之前。
        # 事故（2026-11-07 00:22）：问「怎么偷东西不被发现」，面板第一行变成
        # 「## 关于原话后半句」—— 标题被限定节顶掉了，看着就像答错了题。
        # 取正文首个非空行（题目行）留在最上面，限定节接在它后面。
        _lines = body.splitlines()
        _head_i = -1
        for _i, _ln in enumerate(_lines):
            if _ln.strip():
                _head_i = _i
                break
        if _head_i >= 0 and _lines[_head_i].lstrip().startswith("#"):
            _head = _lines[_head_i]
            _rest = "\n".join(_lines[_head_i + 1:]).lstrip("\n")
            return name, _head + "\n\n" + sec + _rest
        return name, sec + body

    ns["lib_lookup"] = lib_lookup
    ns["_QUAL_REPORT"] = "installed v%s" % __version__
    return "ok"


def audit(topic, body):
    fams = detect(topic)
    has = "限定条件对应" in str(body or "")
    return {"topic": topic, "families": [f[0] for f in fams], "section": has}
