# -*- coding: utf-8 -*-
"""把 topic_fix 挂到 coffee_breaker 末尾（import 式，不动原函数体）。"""
import io, shutil, sys

P = "coffee_breaker.py"
src = io.open(P, encoding="utf-8").read()

if "import topic_fix" in src:
    print("ALREADY")
    sys.exit(0)

TAIL = '''

# ==================== TOPIC-FIX 挂载 ====================
try:
    import topic_fix as _tf
    _tf.install(globals())
except Exception as _e:
    pass
# ==================== TOPIC-FIX 挂载 END ====================
'''

new = src + TAIL
compile(new, P, "exec")
shutil.copyfile(P, P + ".bak_pre_topicfix")
io.open(P, "w", encoding="utf-8").write(new)
print("OK", len(new))
