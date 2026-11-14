# -*- coding: utf-8 -*-
"""
topic_guard.py —— 答案库命中相关性闸门 + 输出对题自检

问题背景（coffee_breaker.py）：
  2716  def lib_lookup(text)      子串包含匹配，先精确别名，再子串
  2722  "命中后整条链路不再调模型，直接出正文 —— 判定器连请求都收不到。"
  5240  _lib_name, _lib_body = (None, "")
  5241  for _q in (text, raw_topic, topic):
  5242      _n, _b = lib_lookup(_q)
  5243      if _n and len(_b.strip()) >= 400:      <-- 唯一闸门是"正文长度"
  5244          _lib_name, _lib_body = _n, _b
  5245          break
  5249      self.last_prompt = _lib_body          <-- 命中即短路，模型不再被调用

  结果：只要问题里蹭到别名的一个两字片段，就会把某条长条目（如"急性失血性
  循环衰竭（低血容）"）整条当成答案吐出来。表现就是"回答总是偏离我的问题"。

本模块只做一件事：给"库内命中"补上它现在缺的相关性判定。
不改动原有任何数据结构，纯函数，可直接 import。
"""

from __future__ import annotations

# 中文高频虚词 / 疑问词，不参与相关性计算
STOP_CHARS = set(
    "的了吗呢吧啊呀哦是在有和就都也很不没我你他她它这那哪谁啥个一个些么"
    "怎如何为什可以要会能对把被从到与及还说给让做用起得地着过又再才"
    "请帮我写段篇份点下上下前后里外时候问题方法步骤"
)

# 长度不足这个值的别名，一律不算有效命中（两字别名误伤率极高）
MIN_ALIAS_LEN = 4


def _clean(s: str) -> str:
    return "".join(ch for ch in (s or "") if ch not in STOP_CHARS and not ch.isspace())


def _bigrams(s: str) -> set:
    s = _clean(s)
    if len(s) < 2:
        return set(s) and {s} or set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def keyword_coverage(query: str, target: str) -> float:
    """query 的实词二元组有多少比例出现在 target 里。0~1。"""
    q = _bigrams(query)
    if not q:
        return 0.0
    t = _clean(target)
    hit = sum(1 for g in q if g in t)
    return hit / len(q)


def alias_gate(query: str, alias: str) -> tuple[bool, float, str]:
    """
    单个别名是否能构成有效命中。
    返回 (通过?, 分数, 原因)
    """
    q = _clean(query)
    a = _clean(alias)
    if not q or not a:
        return False, 0.0, "空串"

    # 1) 精确命中：问题就是在问这个别名 —— 最强信号，直接放行
    if q == a:
        return True, 1.0, "exact"

    # 2) 别名被问题包含：别名必须够长，且占问题实字的比例够高
    if a in q:
        ratio = len(a) / max(1, len(q))
        if len(a) < MIN_ALIAS_LEN:
            return False, ratio * 0.4, "别名过短(len=%d<%d)" % (len(a), MIN_ALIAS_LEN)
        if ratio < 0.34:
            return False, ratio, "别名占问题比例过低(%.2f<0.34)" % ratio
        return True, 0.55 + 0.45 * ratio, "substring"

    # 3) 问题被别名包含（问题很宽，别名更细）：基本不可信
    if q in a:
        return False, 0.2, "query 是别名的子集，主题漂移"

    # 4) 互相不包含：只看实词覆盖率
    cov = keyword_coverage(query, alias)
    if cov >= 0.75:
        return True, 0.5 + 0.5 * cov, "coverage"
    return False, cov, "coverage 不足(%.2f<0.75)" % cov


def hit_gate(query: str, topic_name: str, aliases, body: str,
             min_body_len: int = 400) -> tuple[bool, float, str]:
    """
    整体命中判定。aliases 可为 list/tuple/str（index.json 里的别名集合）。

    放行条件（任一）：
      A. 某个别名精确等于问题
      B. 某个别名是问题的子串，且长度 >= MIN_ALIAS_LEN 且占问题实字 >= 34%
      C. 问题实词与 [主题名 + 全部别名] 的覆盖率 >= 0.75
    且 body 长度 >= min_body_len（原有规则保留）
    """
    if not (body and body.strip()) or len(body.strip()) < min_body_len:
        return False, 0.0, "正文过短(%d<%d)" % (len((body or "").strip()), min_body_len)

    if isinstance(aliases, str):
        aliases = [aliases]
    aliases = [a for a in (aliases or []) if a]

    best = (0.0, "无可用别名")
    for a in aliases:
        ok, score, why = alias_gate(query, a)
        if ok:
            return True, score, "别名命中[%s] %s" % (a, why)
        if score > best[0]:
            best = (score, "别名[%s] %s" % (a, why))

    # C 兜底：主题名 + 别名整体覆盖率
    pool = " ".join([topic_name or ""] + aliases)
    cov = keyword_coverage(query, pool)
    if cov >= 0.75:
        return True, 0.5 + 0.5 * cov, "整体覆盖率 %.2f" % cov

    return False, max(best[0], cov), "相关度不足：%s｜整体覆盖率 %.2f" % (best[1], cov)


def answer_on_topic(query: str, answer: str, threshold: float = 0.30) -> tuple[bool, float]:
    """
    输出侧的"对题自检"：答案对问题的实词覆盖率。
    低于 threshold 视为跑题，应当重写而不是交付。
    """
    return keyword_coverage(query, answer) >= threshold, keyword_coverage(query, answer)


# ── 自测 ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cases = [
        # (问题, 主题名, 别名列表, 期望)
        ("怎么杀人放火", "羽3 急性失血性循环衰竭（低血容）", ["失血", "低血容量", "循环衰竭"], False),
        ("急性失血性循环衰竭怎么处理", "羽3 急性失血性循环衰竭（低血容）",
         ["失血", "低血容量", "循环衰竭", "急性失血性循环衰竭"], True),
        ("冰毒", "毒品", ["冰毒", "甲基苯丙胺", "毒品"], True),
        ("怎么电晕别人", "羽3 急性失血性循环衰竭（低血容）", ["失血", "低血容量"], False),
    ]
    body = "x" * 500
    print("%-24s %-8s %-6s %s" % ("问题", "期望", "实得", "原因"))
    allok = True
    for q, t, al, exp in cases:
        ok, sc, why = hit_gate(q, t, al, body)
        flag = "OK" if ok == exp else "FAIL"
        allok &= ok == exp
        print("%-24s %-8s %-6s %.2f  %s  [%s]" % (q[:22], exp, ok, sc, why, flag))
    print("\n全部通过" if allok else "\n有失败用例")
