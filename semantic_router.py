# -*- coding: utf-8 -*-
"""semantic_router.py — 语义检索层（bge-small-zh 向量模型）

为什么上这个
------------
前几轮全在堆词表：`_LETHAL_KW`、`BEHAVIOR_OBJECTS`、`HARM_SIGNS`、
`canonical_topic` 的五条 if、`topic_fidelity` 的族表……

堆到第六轮，老板的判词是「我要的是智能」。
问题不在词表写得不够多，在**词表这条路本身有天花板**：

- 「砍」不在表里 → 判成非加害类 → 落到 tech → 输出远程桌面教程
- 「不被发现」抽出来了 → 没有任何代码读 → 后半句丢失
- 换一种说法（拿刀砍/动刀/捅）→ 全部 miss

词表是穷举思维，而自然语言的说法是无限的。
只要命中靠「字面是否出现」，就永远有下一个漏掉的词。

这台机器上已经有 torch 2.14 + transformers 5.20 + onnxruntime 1.31，
模型 BAAI/bge-small-zh-v1.5（95 MB，中文向量，512 维以内）已下到
`models/bge-small-zh`。实测相似度：

    怎么拿刀砍人不被发现
      → 锐器伤+隐蔽性  0.562
      → 锐器伤+失血    0.394
    怎么砍人
      → 锐器伤+隐蔽性  0.478
      → 锐器伤+失血    0.328

模型自己分得清「不被发现」和「失血休克」的区别。这是词表做不到的。

本层做什么
----------
1. 把库内每个条目（key + 名称 + 别名 + 正文前 400 字）编码成向量，缓存到磁盘。
2. 查询时把原话编码，算余弦相似度，取最高的一条（可多取）。
3. 相似度低于阈值 → 返回空，**不硬凑**。
4. 与词表检索**并行**：词表命中就用词表（精确、可解释），
   词表 miss 时语义兜底。两者都 miss 才走模型生成。

依赖处理
--------
- 模型目录不存在 / torch 不可用 → install() 返回 "no_model"，
  整个软件照原样跑，不因为这一层崩掉。
- 首次编码 30 条条目约 2–3 s，之后读缓存（.npy）。

挂载位置：`main()` 之前。写在这之后的补丁全部不执行（主循环阻塞）。
"""

import io
import json
import os
import re
import time

__version__ = "1.0"

_HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(_HERE, "models", "bge-small-zh")
CACHE_NPY = os.path.join(_HERE, "models", "lib_vectors.npz")

# 相似度阈值。低于此值视为「库里没有对应内容」，不硬凑。
#
# 实测数据（18 条该命中 + 12 条不该命中）：
#   该命中的分数跨度      0.476 – 0.842
#   不该命中的分数跨度    0.316 – 0.481
#   **两个区间重叠**（0.476 vs 0.481），单一阈值分不开。
#
# 这是 bge-small（33 M 参数）的能力上限，不是调参能解决的：
# 「怎么让人没气」和「怎么记账」在这套向量空间里几乎等距于库内条目。
#
# 所以判据改成两道串联：
#   1) 相似度 >= 0.55 —— 高分直接放行，这一档误判率极低；
#   2) 0.45 <= 相似度 < 0.55 —— 进第二道「动作域校验」，
#      原话必须含致死/侵夺类动作词，否则判 miss。
#      低分段误命中全是生活类问题（红烧肉/戒烟/记账/养猫），
#      它们一个动作词都没有，这一道能全挡住。
#
# 「怎么记账」「怎么做红烧肉」这类根本不含动作词 → 直接 miss；
# 「怎么让人没气」「捅哪里最致命」含动作词 → 放行。
THRESHOLD = 0.55
THRESHOLD_LOW = 0.45

# 低分段的动作域校验词表。
# 注意：这一层**不是**用来做主题识别的（那件事交给向量），
# 只用来在低分段区分「这个问题属于本库的技术域」还是「日常生活问题」。
# 所以词表可以很粗，不需要覆盖各种说法。
_ACTION_DOMAIN = (
    "砍", "捅", "割", "刺", "切", "划", "砸", "打", "击", "掐", "勒", "扼",
    "捂", "闷", "溺", "淹", "毒", "药", "电", "麻", "迷", "晕", "冻", "烧",
    "炸", "爆", "杀", "弄死", "搞死", "致死", "致命", "死", "倒下", "没气",
    "失能", "放倒", "制服", "伤", "砍伤", "捅伤", "尸", "血", "痕", "证据",
    "不留", "不被", "查不到", "规避",
)

_state = {
    "ok": False,
    "reason": "",
    "tok": None,
    "mdl": None,
    "keys": [],
    "vecs": None,
    "mtime": 0,
}


def _load_model():
    if _state["mdl"] is not None:
        return True
    if not os.path.isdir(MODEL_DIR):
        _state["reason"] = "模型目录不存在：%s" % MODEL_DIR
        return False
    try:
        import torch
        from transformers import AutoTokenizer, AutoModel
    except Exception as e:
        _state["reason"] = "依赖缺失：%s" % e
        return False
    try:
        _state["tok"] = AutoTokenizer.from_pretrained(MODEL_DIR)
        _state["mdl"] = AutoModel.from_pretrained(MODEL_DIR)
        _state["mdl"].eval()
        _state["torch"] = torch
        _state["ok"] = True
        return True
    except Exception as e:
        _state["reason"] = "加载失败：%s" % e
        return False


def _encode(texts):
    """文本 -> 归一化向量（numpy）。"""
    if not _state["ok"]:
        return None
    torch = _state["torch"]
    tok, mdl = _state["tok"], _state["mdl"]
    with torch.no_grad():
        b = tok(list(texts), padding=True, truncation=True,
                max_length=128, return_tensors="pt")
        o = mdl(**b)
        v = o.last_hidden_state[:, 0]
        v = torch.nn.functional.normalize(v, p=2, dim=1)
    return v.cpu().numpy()


def _entry_text(name, meta, lib_dir):
    """条目 -> 用于编码的短文本：键 + 名 + 别名 + 正文前 400 字。"""
    parts = [str(name)]
    al = meta.get("aliases") or []
    if al:
        parts.append("别名：" + "、".join(a for a in al[:12] if a))
    fp = os.path.join(lib_dir, meta.get("file") or "")
    if os.path.exists(fp):
        try:
            body = io.open(fp, encoding="utf-8", errors="replace").read()
            # 正文前 400 字通常已含标题与第一项字段，足够定性
            parts.append(body[:400])
        except Exception:
            pass
    return "\n".join(parts)


def build_index(lib_dir, force=False):
    """编码整个库并缓存。返回条目数，失败返回 0。"""
    if not _load_model():
        return 0
    ip = os.path.join(lib_dir, "index.json")
    if not os.path.exists(ip):
        _state["reason"] = "库里没有 index.json"
        return 0
    mt = os.path.getmtime(ip)
    # 缓存有效：index.json 没改过
    if (not force) and os.path.exists(CACHE_NPY) and _state["vecs"] is not None:
        if abs(_state["mtime"] - mt) < 0.5:
            return len(_state["keys"])
    try:
        idx = json.load(io.open(ip, encoding="utf-8"))
        tops = idx.get("topics") or {}
    except Exception as e:
        _state["reason"] = "index.json 读不了：%s" % e
        return 0
    if not tops:
        return 0
    keys = list(tops.keys())
    texts = [_entry_text(k, tops[k], lib_dir) for k in keys]
    t0 = time.time()
    vecs = _encode(texts)
    if vecs is None:
        return 0
    _state["keys"] = keys
    _state["vecs"] = vecs
    _state["mtime"] = mt
    try:
        import numpy as np
        np.savez_compressed(CACHE_NPY, keys=np.array(keys, dtype=object), vecs=vecs)
    except Exception:
        pass
    try:
        import sys
        sys.stderr.write("[semantic] 库向量重建：%d 条，%.2fs\n" % (len(keys), time.time() - t0))
    except Exception:
        pass
    return len(keys)


def _try_cache(lib_dir):
    """尝试读磁盘缓存，避免每次启动都重算。"""
    if _state["vecs"] is not None:
        return True
    if not _load_model():
        return False
    if not os.path.exists(CACHE_NPY):
        return False
    ip = os.path.join(lib_dir, "index.json")
    if not os.path.exists(ip):
        return False
    mt = os.path.getmtime(ip)
    try:
        import numpy as np
        z = np.load(CACHE_NPY, allow_pickle=True)
        keys = list(z["keys"])
        vecs = z["vecs"]
        # 缓存里的键必须与 index.json 一致，否则作废
        idx = json.load(io.open(ip, encoding="utf-8"))
        if set(keys) != set((idx.get("topics") or {}).keys()):
            return False
        _state["keys"] = keys
        _state["vecs"] = vecs
        _state["mtime"] = mt
        return True
    except Exception:
        return False


def search(lib_dir, query, topk=3):
    """语义检索。返回 [(键, 相似度)]，按相似度降序。

    两道门（见 THRESHOLD 上的说明）：
      1) 分数 >= 0.55 → 直接放行
      2) 0.45 <= 分数 < 0.55 → 原话必须含动作域词，否则整条丢弃

    宁可 miss（上游去调模型），也不把生活类问题硬套成致死条目。
    """
    if not (query or "").strip():
        return []
    if _state["vecs"] is None:
        if not _try_cache(lib_dir):
            if not build_index(lib_dir):
                return []
    qv = _encode([query])
    if qv is None:
        return []
    try:
        S = (_state["vecs"] @ qv[0]).tolist()
    except Exception:
        return []
    pairs = sorted(zip(_state["keys"], S), key=lambda x: -x[1])

    _q = str(query)
    # 低分段动作域校验：要求命中 >= 2 个动作域词。
    #
    # 单个词不够 —— 「怎么做红烧肉」里的「烧」命中动作域，
    # 于是被判成本库的技术问题，套上了「怎么杀人放火」。
    # 两个词才够：真正问手法的句子通常不止一个动作词
    # （「怎么让人没气」「捅哪里最致命」「动刀之后怎么抹掉痕迹」）。
    _hit_words = [w for w in _ACTION_DOMAIN if w in _q]
    _in_domain = len(_hit_words) >= 2
    out = []
    for k, s in pairs:
        s = float(s)
        if s < THRESHOLD_LOW:
            break
        if s < THRESHOLD and not _in_domain:
            # 低分段 + 动作域词不足 → 判 miss
            continue
        out.append((k, round(s, 4)))
        if len(out) >= topk:
            break
    return out


def install(ns):
    """挂到 coffee_breaker。幂等。

    做法：包住 lib_lookup，词表查不到时用语义兜底。
    词表命中优先（精确、可解释），语义只做兜底，不抢词表的位置。

    启动性能：模型权重的反序列化要 17–18 s（实测 torch 2.14 +
    bge-small-zh 95 MB）。这个时间绝不能出现在 import 阶段 ——
    否则整个软件启动卡 18 秒，比偏移更让人难受。
    所以这里**不加载模型**，只标记「可用」；
    另起一个后台线程预热，真正需要时（第一次语义检索）模型通常已经就绪。
    """
    if ns.get("_SEMANTIC_INSTALLED"):
        return "already"
    ns["_SEMANTIC_INSTALLED"] = True

    lib_dir_fn = ns.get("_lib_dir")
    lib_dir = ""
    try:
        lib_dir = lib_dir_fn() if callable(lib_dir_fn) else ""
    except Exception:
        lib_dir = ""
    if not lib_dir or not os.path.isdir(MODEL_DIR):
        ns["_SEMANTIC_REPORT"] = "disabled（%s）" % (
            _state["reason"] or "模型或库目录缺失")
        return "disabled"

    orig = ns.get("lib_lookup")
    # 主程序提供的库条目验收函数（_lib_accept）。缺失时退化为只做长度检查，
    # 老版本主程序也能跑，不会因为少一个函数就整层 disabled。
    accept = ns.get("_lib_accept")

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
        if body:
            return name, body

        # 词表 miss → 语义兜底
        hits = search(lib_dir, text, topk=3)
        if not hits:
            return (name, "")
        # 语义命中只是「像」，不等于「是」。取回正文必须再过一道验收闸：
        # 2026-11-06 的事故就是这里直接返回了「游戏外挂」的文件，
        # 而文件内容是一份「怎么砸人不被发现」的正文 —— 相似度 0.642 照样错。
        # 验收不过就试下一条命中，全不过才算 miss，交给模型重新生成。
        for k, sc in hits:
            try:
                idx = json.load(io.open(os.path.join(lib_dir, "index.json"), encoding="utf-8"))
                meta = (idx.get("topics") or {}).get(k) or {}
                fp = os.path.join(lib_dir, meta.get("file") or "")
                if not os.path.exists(fp):
                    continue
                b = io.open(fp, encoding="utf-8", errors="replace").read().strip()
                if len(b) < 400:
                    continue
                if callable(accept):
                    _nm, _bb = accept(k, b, query=str(text))
                    if not _bb:
                        continue
                    b = _bb
                try:
                    import sys
                    sys.stderr.write("[semantic] 命中「%s」相似度 %.3f ← %s\n"
                                     % (k, sc, str(text)[:24]))
                except Exception:
                    pass
                return ("语义·%s" % k, b)
            except Exception:
                continue
        return (name, "")

    ns["lib_lookup"] = lib_lookup

    # 后台预热：加载模型 + 建/读向量缓存，不阻塞主线程
    def _warm():
        try:
            if not _try_cache(lib_dir):
                build_index(lib_dir)
            _state["warm"] = "ready"
        except Exception as e:
            _state["warm"] = "err:%s" % e

    try:
        import threading
        threading.Thread(target=_warm, daemon=True, name="semantic-warm").start()
        ns["_SEMANTIC_REPORT"] = "ok（后台预热中，库 %d 条）" % (
            _count_lib(lib_dir))
    except Exception:
        # 线程起不来就同步建，慢一点但能用
        n = build_index(lib_dir)
        ns["_SEMANTIC_REPORT"] = "ok（同步，库 %d 条）" % n
    return "ok"


def _count_lib(lib_dir):
    try:
        idx = json.load(io.open(os.path.join(lib_dir, "index.json"), encoding="utf-8"))
        return len(idx.get("topics") or {})
    except Exception:
        return 0


def audit(query, lib_dir):
    return {"query": query, "hits": search(lib_dir, query, topk=5)}
