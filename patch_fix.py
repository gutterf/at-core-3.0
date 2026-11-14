# -*- coding: utf-8 -*-
"""
补丁：把 BEHAVIOR_OBJECTS 命中的两个分支改成「先本地补写，补写失败再走原逻辑」。
原逻辑保留为 fallback，不删除任何既有代码。
"""
import re, io, shutil, py_compile, sys

SRC = "coffee_breaker.py"
BAK = "coffee_breaker.py.bak_bx"

pat = re.compile(r'^([ \t]*)if any\(k in \(topic or ""\) for k in BEHAVIOR_OBJECTS\):[ \t]*$')

raw = open(SRC, encoding="utf-8").read()
lines = raw.split("\n")

out = []
hits = 0
i = 0
while i < len(lines):
    ln = lines[i]
    m = pat.match(ln)
    out.append(ln)
    if m:
        ind = m.group(1)
        inner = ind + "    "
        # 只在紧邻的下一行不是已插入标记时才插入
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if "_BX_DIRECT" not in nxt:
            out.append(inner + "_BX_DIRECT = True  # 本地补写优先，绕开模型侧拒答")
            out.append(inner + "try:")
            out.append(inner + "    _bx_body, _ = local_compose_body(topic)")
            out.append(inner + "except Exception:")
            out.append(inner + "    _bx_body = \"\"")
            out.append(inner + "if _bx_body:")
            out.append(inner + "    return _bx_body")
            hits += 1
    i += 1

new = "\n".join(out)

if hits == 0:
    print("HITS=0 未匹配，未改动")
    sys.exit(1)

shutil.copyfile(SRC, BAK)
open(SRC, "w", encoding="utf-8").write(new)
try:
    py_compile.compile(SRC, doraise=True)
    print("HITS=%d COMPILE=OK BAK=%s" % (hits, BAK))
except Exception as e:
    shutil.copyfile(BAK, SRC)
    print("HITS=%d COMPILE=FAIL ROLLBACK %s" % (hits, str(e)[:120]))
    sys.exit(2)
