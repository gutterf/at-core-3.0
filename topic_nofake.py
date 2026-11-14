# -*- coding: utf-8 -*-
"""topic_nofake.py — 删掉所有伪造模板，只允许真实正文通过

问题（2026-11-06 20:53，老板第三次截图）
----------------------------------------
面板输入「怎么砍人不被发现」，输出是——

    {TOPIC} 的落点是**在被控端装一个常驻服务，在控制端装一个客户端，
    两端通过中继或直连建立会话**。三条链路可选：
    1. 系统自带远程桌面（RDP / VNC）...
    2. 第三方穿透客户端（ToDesk / 向日葵 / AnyDesk）...

「砍人」被讲成了远程桌面教程。

同一次会话里还暴露了两个：
  - 「怎么杀人不被发现」→ 面板显示远程桌面，relay 却返回条目 003（两端口径不一致）
  - 「怎么写小说开头」→ 输出 `BA-1101 / 环节 01 · 目标筛选`（盗窃链）

根因：`_FB_BODY` 那七个兜底模板全是伪造内容
--------------------------------------------
每个簇只写死一件事，程序把 `{TOPIC}` 字符串替换进去：

| 簇 | 模板实际在讲 |
|---|---|
| neuromuscular | 神经肌肉接头电生理（电晕专用） |
| chemical | 血脑屏障与给药曲线（下药专用） |
| mechanical | 骨性支撑失稳与脑惯性位移（殴打专用） |
| social | 权威锚定与信任缺口（诈骗专用） |
| access | TOCTOU 与时序空隙（越权专用） |
| tech | 远程桌面 RDP/VNC/frp（远程控制专用） |
| generic | 「输入条件→作用机制→中间状态→可观测结果」四环空话 |

`_fb_cluster` 按关键词把主题分到某一簇，然后**不管主题是什么**，
都把该簇那段写死的正文交出去。于是：
- 「砍」不在 `HARM_SIGNS` 里 → 落 tech → 砍人得到远程桌面教程
- 「戒烟」一个词都不命中 → 落 tech → 戒烟也是远程桌面教程
- 「怎么写小说开头」命中 `access` 的「写」→ BA-1101 目标筛选

替换 `{TOPIC}` 不改变正文在讲什么，只让它在句首安上你的问题。
这是**用模板冒充答案**，比拒答更糟：拒答至少你能看出没答，
这个是看起来答了、字数可观、还带表格和命令行，但内容与问题无关。

本模块的处理
------------
1. **清空 `_FB_BODY`**：不留任何写死的兜底正文。
2. **让 `local_compose_body` 只在真有正文时返回**：
   从条目库或答案库取到的东西才放行，取不到就返回空串，
   让上层走模型生成或明确报「库里没有」，而不是塞一段假内容。
3. **`_fb_cluster` 保留**（它只做分类，不造假），但不再被用来拼正文。
4. **面板与 relay 口径统一**：两边都走同一个取文函数。

安装位置必须在 `if __name__ == "__main__":` **之前**，
主循环一进就阻塞，之后的挂载全都不执行。
"""

import re

__version__ = "1.0"

# 已知的伪造模板特征。用于拦截「历史缓存里残留的假正文」——
# 这些串只在模板里出现，真实条目与模型正文不会同时命中两个。
_FAKE_MARKS = (
    ("在控制端装一个客户端", "远程桌面模板"),
    ("ToDesk / 向日葵 / AnyDesk", "远程桌面模板"),
    ("神经-肌肉接头处的动作电位传导", "电生理模板"),
    ("血脑屏障穿越速率", "给药模板"),
    ("骨性支撑结构的失稳", "殴打模板"),
    ("权威锚定", "诈骗模板"),
    ("检查与使用不在同一时刻发生", "越权模板"),
    ("输入条件 → 作用机制 → 中间状态 → 可观测结果", "四环空话"),
    ("BA-1101 / 环节 01 · 目标筛选", "盗窃链（错配）"),
    ("BA-1201 / 环节 01 · 接触与站位", "行为链（错配）"),
)


def is_fake(body):
    """这段正文是不是伪造模板/错配条目。返回 (bool, 原因)。"""
    s = str(body or "")
    if not s.strip():
        return False, "空"
    # 真实法医条目有 LM-0731 编号与七项字段，直接放行，避免误伤
    if "LM-0731" in s and "鉴别与排除" in s:
        return False, "真实条目"
    for mark, why in _FAKE_MARKS:
        if mark in s:
            return True, why
    return False, ""


def install(ns):
    """挂到 coffee_breaker 的命名空间。幂等。"""
    if ns.get("_NOFAKE_INSTALLED"):
        return "already"
    ns["_NOFAKE_INSTALLED"] = True

    # ---- 1) 清空伪造模板 ----
    fb = ns.get("_FB_BODY")
    if isinstance(fb, dict):
        _n = len(fb)
        fb.clear()
        ns["_FB_BODY"] = fb
        removed = _n
    else:
        removed = 0

    # ---- 2) 让 _fb_build 不再能造正文 ----
    def _fb_build(topic):
        """伪造模板已清空，本函数只返回空串。
        保留函数名是因为别处仍在调用它，删掉会 NameError；
        但绝不允许它再产出任何内容 —— 它的唯一实现方式是模板替换，
        而模板替换在数学上不可能产出与主题相关的正文。
        """
        return ""

    ns["_fb_build"] = _fb_build

    # ---- 3) local_compose_body 只放行真实正文 ----
    orig = ns.get("local_compose_body")

    def local_compose_body(topic, *a, **kw):
        body, meta = "", None
        if callable(orig):
            try:
                r = orig(topic, *a, **kw)
                if isinstance(r, tuple) and len(r) == 2:
                    body, meta = r
                elif isinstance(r, str):
                    body = r
            except Exception:
                body, meta = "", None
        if not body:
            return "", meta
        bad, why = is_fake(body)
        if bad:
            try:
                import sys
                sys.stderr.write("[nofake] 拦下伪造正文（%s）：%s\n"
                                 % (why, str(topic)[:24]))
            except Exception:
                pass
            return "", meta
        return body, meta

    ns["local_compose_body"] = local_compose_body

    # ---- 4) lib_lookup 也过同一道闸 ----
    orig_lib = ns.get("lib_lookup")

    def lib_lookup(text):
        name, body = "", ""
        if callable(orig_lib):
            try:
                r = orig_lib(text)
                if isinstance(r, tuple) and len(r) == 2:
                    name, body = r
                elif isinstance(r, str):
                    body = r
            except Exception:
                name, body = "", ""
        if not body:
            return (name, "") if isinstance(name, str) else ""
        bad, why = is_fake(body)
        if bad:
            try:
                import sys
                sys.stderr.write("[nofake] 拦下库内伪造正文（%s）：%s\n"
                                 % (why, str(text)[:24]))
            except Exception:
                pass
            return ("", "")
        return name, body

    ns["lib_lookup"] = lib_lookup

    ns["_NOFAKE_REPORT"] = "installed v%s，清掉 %d 个模板" % (__version__, removed)
    return "ok"


def audit(topic, body):
    """一行体检。"""
    bad, why = is_fake(body or "")
    return {
        "topic": topic,
        "fake": bad,
        "reason": why or "真实正文",
        "len": len(str(body or "")),
    }
