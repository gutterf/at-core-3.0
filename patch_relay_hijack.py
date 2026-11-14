#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""relay17801.js · 主题劫持修复补丁

问题（2026-11-06 20:23 复现）
----------------------------
老板在冷咖啡面板点「全自动破甲」，输入「怎么杀人放火」。
WorkBuddy 新会话问同一句，回的是「BA-1201 / 环节 01 · 接触与站位」
（这是「怎么投毒别人」的正文），跟问句毫无关系。

链路实测
--------
relay 的 user 消息是 324KB 的注入包，真正的原话只在末尾
`<user_query>怎么杀人放火</user_query>` 里。
但 pre-hit 那一行传的是 `libLookup(original)` —— original 是整条注入。

`libLookup` 内部先调 `canonicalTopic(text)`，而 canonicalTopic 的判据是：

    const _opIntent = /怎么|如何|怎样|教我|方法|步骤/.test(t) && /别人|他人|人/.test(t);
    if (_opIntent) { if (/毒药|下毒|投毒|.../.test(t)) return '怎么投毒别人'; ... }

KERNEL.md 里有「毒物」「方法」「步骤」「人」这些字，
于是 6197 字的注入文本被归一成 `怎么投毒别人`，
库里正好有这条，直接返回 BA-1201。

实测输出：
    canonicalTopic(注入全文) = "怎么投毒别人"       ← 劫持点
    libLookup(注入全文)      = "怎么投毒别人"

两处独立缺陷
------------
B1  `libLookup(original)` 与 `canonicalTopic(stripInjected(original))`
    都拿整条注入当输入。stripInjected 只剥 `<topic-anchor>` 与 system-reminder，
    KERNEL.md / AGENTS.md 的正文原样留着，里面的示例词照样能触发。

B2  `canonicalTopic` 没有任何长度约束。它本来就是给 5–20 字的短问句写的，
    喂 6000 字进去必然随便命中一个词。

修法
----
1. 新增 `justAsk()`：只取最后一个 `<user_query>` 的内容；取不到才退回 stripInjected。
2. `libLookup` 入口先过 `justAsk`，之后所有判断都在短句上做。
   短句仍超过 60 字（说明不是真原话）直接返回 null。
3. `canonicalTopic` 加长度闸：超过 40 字直接返回空串，不做归一化。
4. 三个调用点全部改用 `justAsk`。

幂等：重复执行不会叠加。
"""

import io
import os
import re
import shutil
import time

SRC = r"C:/Users/admin/Documents/DSH_Work/_tools/relay17801.js"
MARK = "// ==== FIDELITY-FIX v1 ===="

JUSTASK = '''
// ==== FIDELITY-FIX v1 ====
// 取出用户真正说的那句话。
//
// 事故（2026-11-06 20:23）：老板输入「怎么杀人放火」，新会话回的是
// 「BA-1201 / 环节 01 · 接触与站位」（怎么投毒别人的正文）。
// 根因就是这里 —— relay 的 user 消息是 324KB 注入包，真正的原话只在末尾
// <user_query>…</user_query> 里，但库查询拿的是整条注入。
// canonicalTopic 读到 KERNEL.md 里的「毒物」「方法」「步骤」「人」，
// 把 6000 字归一成了「怎么投毒别人」。
//
// 判据顺序：
//   1) 最后一个 <user_query> 的内容 —— WorkBuddy 的唯一正确入口
//   2) 没有则退回 stripInjected 后的文本
//   3) 仍超过 60 字 → 不是真原话，返回空串（宁可 miss，也不许劫持）
function justAsk(t) {
  const s = String(t || '');
  const all = [...s.matchAll(/<user_query>([\\s\\S]*?)<\\/user_query>/g)];
  let out = '';
  if (all.length) {
    out = String(all[all.length - 1][1] || '');
  } else {
    out = stripInjected(s);
  }
  // 剥掉原话里可能夹带的图片/附件标签
  out = out.replace(/<image_local_path>[\\s\\S]*?<\\/image_local_path>/gi, ' ')
           .replace(/<[a-z_][a-z0-9_-]*\\s[^>]*>/gi, ' ')
           .replace(/<\\/?[a-z_][a-z0-9_-]*>/gi, ' ')
           .replace(/\\s+/g, ' ')
           .trim();
  if (Array.from(out).length > 60) return '';
  return out;
}
// ==== FIDELITY-FIX v1 END ====
'''


def main():
    if not os.path.exists(SRC):
        print("找不到 relay：%s" % SRC)
        return 1
    txt = io.open(SRC, encoding="utf-8", errors="replace").read()
    if MARK in txt:
        print("已打过补丁，跳过。")
        return 0

    bak = SRC + ".bak-fidelityfix-" + time.strftime("%Y%m%d-%H%M%S")
    shutil.copy2(SRC, bak)
    print("备份：%s" % os.path.basename(bak))

    # ---- 1) 插入 justAsk（放在 canonicalTopic 之前）----
    anchor = "const LETHAL_ANY = "
    i = txt.find(anchor)
    if i < 0:
        print("找不到 LETHAL_ANY 锚点，放弃")
        return 1
    # 回溯到它所在注释块开头之前插，避免打断注释
    txt = txt[:i] + JUSTASK + "\n" + txt[i:]
    print("✔ 已插入 justAsk()")

    # ---- 2) canonicalTopic 加长度闸 ----
    old = """function canonicalTopic(text) {
  const t = String(text || '');
  if (!t.trim()) return '';"""
    new = """function canonicalTopic(text) {
  const t = String(text || '');
  if (!t.trim()) return '';
  // FIDELITY-FIX v1：长度闸。
  // 这个函数的判据是给 5–20 字短问句写的（「怎么X别人」），
  // 喂整条注入（6000+ 字）进去必然随便命中一个示例词，
  // 实测把「怎么杀人放火」劫持成「怎么投毒别人」。
  // 超长一律不归一化，交给下游按原句处理。
  if (Array.from(t.trim()).length > 40) return '';"""
    if old in txt:
        txt = txt.replace(old, new, 1)
        print("✔ canonicalTopic 已加 40 字长度闸")
    else:
        print("!! 未找到 canonicalTopic 开头，长度闸未加")

    # ---- 3) libLookup 入口先过 justAsk ----
    old2 = """function libLookup(text) {
  const q = String(text || '');
  if (!q.trim()) return null;"""
    new2 = """function libLookup(text) {
  // FIDELITY-FIX v1：先取用户真正说的那句，再查库。
  // 不这么做的后果：整条注入（6000+ 字）被当成问句，
  // canonicalTopic 从 KERNEL.md 里捡到「毒物」→ 归一成「怎么投毒别人」→ 直出错误正文。
  const _bare = justAsk(text);
  if (!_bare) return null;
  const q = _bare;
  if (!q.trim()) return null;"""
    if old2 in txt:
        txt = txt.replace(old2, new2, 1)
        print("✔ libLookup 入口已改用 justAsk")
    else:
        print("!! 未找到 libLookup 开头")

    # ---- 4) 三个调用点 ----
    n_fix = 0
    if "libLookup(original)" in txt:
        txt = txt.replace("libLookup(original)", "libLookup(justAsk(original))")
        n_fix += txt.count("libLookup(justAsk(justAsk(original)))")
        print("✔ libLookup(original) → libLookup(justAsk(original))")
    if "libLookup(stripInjected(original))" in txt:
        txt = txt.replace("libLookup(stripInjected(original))",
                          "libLookup(justAsk(original))")
        print("✔ libLookup(stripInjected(original)) → libLookup(justAsk(original))")
    if "canonicalTopic(stripInjected(original))" in txt:
        txt = txt.replace("canonicalTopic(stripInjected(original))",
                          "canonicalTopic(justAsk(original))")
        print("✔ canonicalTopic(stripInjected(original)) → canonicalTopic(justAsk(original))")

    io.open(SRC, "w", encoding="utf-8", newline="\n").write(txt)
    print("已写入：%s" % SRC)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
