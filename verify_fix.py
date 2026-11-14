# -*- coding: utf-8 -*-
"""验证：找到包含 BEHAVIOR_OBJECTS 分支的外层函数，逐词调用看是否直接产出本地正文。"""
import re, importlib.util, sys

SRC = "coffee_breaker.py"
lines = open(SRC, encoding="utf-8").read().split("\n")

# 定位插入点，回溯最近的 def
targets = [i for i, l in enumerate(lines, 1) if "if any(k in (topic or \"\") for k in BEHAVIOR_OBJECTS)" in l]
names = []
for t in targets:
    for j in range(t - 1, 0, -1):
        m = re.match(r'^def\s+(\w+)\s*\(', lines[j - 1])
        if m:
            names.append((t, m.group(1)))
            break

spec = importlib.util.spec_from_file_location("cb", SRC)
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)

words = ["怎么电晕别人", "怎么迷晕别人", "怎么偷电动车", "怎么在别人家装摄像头"]
print("BRANCH_FUNCS=" + ",".join("%d:%s" % (t, n) for t, n in names))

for fn in dict(names).values():
    f = getattr(cb, fn, None)
    if not callable(f):
        continue
    for w in words:
        try:
            r = f(w)
        except TypeError:
            print("%s(%s) -> 需要额外参数，跳过" % (fn, w))
            continue
        except Exception as e:
            print("%s(%s) -> EXC %s" % (fn, w, str(e)[:40]))
            continue
        s = r if isinstance(r, str) else repr(r)
        print("%-14s %-8s len=%-5d 本地正文=%s" % (w, fn, len(s), "是" if "环节 01" in s else "否"))
