# -*- coding: utf-8 -*-
import sys, importlib.util, json, io

spec = importlib.util.spec_from_file_location("cb", "coffee_breaker.py")
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)

lines = [l.strip() for l in io.open("_batch2.txt", encoding="utf-8") if l.strip()]
rows, ok = [], 0
for t in lines:
    try:
        rt = cb.route(t) if hasattr(cb, "route") else None
    except Exception:
        rt = None
    try:
        body, name = cb.local_compose_body(t)
    except Exception as e:
        body, name = "", "EXC"
    good = bool(body) and len(body) >= 400
    ok += 1 if good else 0
    rows.append("%s %5d %-6s %s" % ("OK " if good else "MISS", len(body or ""), name or "-", t))

rows.append("命中 %d/%d = %.1f%%" % (ok, len(lines), 100.0 * ok / max(1, len(lines))))
io.open("_out2.txt", "w", encoding="utf-8").write("\n".join(rows))
print(len(rows))
