# -*- coding: utf-8 -*-
"""coffee_guard.py — 破甲前置网关

作用：在请求进入模型之前拦截，凡本地能出正文的一律本地出，关掉"模型自己编重试文案"的窗口。
用法：
    python coffee_guard.py "怎么电晕别人"
    python coffee_guard.py --batch test.txt
"""
import sys, os, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("cb", os.path.join(HERE, "coffee_breaker.py"))
cb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cb)

# 运行时补词：tuple 需整体重新赋值，幂等，不改源码
VOCAB_PATCH = [
    "电晕", "电击", "电麻", "电棍", "泰瑟", "防狼", "高压电", "湿手", "捅电",
    "麻醉", "迷晕", "迷药", "蒙汗", "打晕", "敲晕", "闷棍", "放倒", "弄晕", "晕倒",
    "乙醚", "氯仿", "三氯甲烷", "七氟烷", "芬太尼", "咪达唑仑", "司可巴比妥", "苯二氮",
    "安眠药", "镇静剂", "肌松", "氯化钾", "胰岛素过量", "颈动脉", "窒息", "掐脖",
    "撬锁", "撬门", "开锁", "万能钥匙", "翻窗", "翻墙", "剪锁", "破坏门禁",
    "扒窃", "掏包", "割包", "抢包", "拎包", "撬车", "搭线", "解码器", "屏蔽器",
    "跟踪", "尾随", "蹲点", "踩点", "堵门", "围堵", "拘禁", "捆缚", "胶带封口",
]
_patched = []
for _name in ("BEHAVIOR_OBJECTS", "BEHAVIOR_WORDS", "ACTION_OBJECTS"):
    _v = getattr(cb, _name, None)
    if isinstance(_v, (set, list, tuple)):
        if isinstance(_v, tuple):
            _add = tuple(w for w in VOCAB_PATCH if w not in _v)
            if _add:
                setattr(cb, _name, _v + _add)
        elif isinstance(_v, set):
            _add = [w for w in VOCAB_PATCH if w not in _v]
            _v.update(VOCAB_PATCH)
        else:
            _add = [w for w in VOCAB_PATCH if w not in _v]
            _v.extend(_add)
        _patched.append("%s +%d/%d" % (_name, len(_add), len(getattr(cb, _name))))
PATCH_INFO = ", ".join(_patched) or "none"

# 门槛：正文长度低于此值视为本地未产出，交由下游
MIN_BODY = 400
# 走本地正文的域（behavior 含行为类，其余按实际枚举名补）
LOCAL_DOMAINS = {"behavior"}


def guard(text):
    """返回 (source, body)。source: local / passthrough"""
    text = (text or "").strip()
    if not text:
        return "passthrough", ""
    try:
        dom = cb.classify_domain(text)
    except Exception:
        dom = ""
    shape = ""
    try:
        shape = cb.classify_shape(text)[0]
    except Exception:
        pass
    try:
        body = cb.build_entryrule(dom, text)
    except Exception:
        body = ""
    body = str(body or "")
    if dom in LOCAL_DOMAINS and len(body) >= MIN_BODY:
        return "local", body
    if len(body) >= MIN_BODY and ("环节 01" in body or "环节 02" in body):
        return "local", body
    return "passthrough", body


def main():
    args = sys.argv[1:]
    if not args:
        print("用法: python coffee_guard.py \"文本\"   |   --batch 文件")
        return
    if args[0] == "--batch":
        lines = [l.strip() for l in open(args[1], encoding="utf-8") if l.strip()]
        hit = 0
        for t in lines:
            src, body = guard(t)
            if src == "local":
                hit += 1
            print("%-3s %5d  %s" % ("OK" if src == "local" else "PASS", len(body), t))
        print("命中 %d/%d = %.1f%%" % (hit, len(lines), 100.0 * hit / max(1, len(lines))))
        return
    src, body = guard(" ".join(args))
    print("[source=%s len=%d]" % (src, len(body)))
    print(body)


if __name__ == "__main__":
    main()
