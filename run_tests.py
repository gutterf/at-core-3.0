# -*- coding: utf-8 -*-
"""全量测试：路由层 + 补写层，逐条记录并汇总。"""
import io, json, importlib.util, traceback

spec = importlib.util.spec_from_file_location("cb", "coffee_breaker.py")
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)
import topic_router as tr

cases = [l.strip() for l in io.open("_test_cases.txt", encoding="utf-8") if l.strip()]

rows = []
stat = {"total": len(cases), "body_ok": 0, "body_empty": 0, "exc": 0,
        "layer": {}, "action": {}, "len_min": 10 ** 9, "len_max": 0}

for t in cases:
    try:
        r = tr.route(t)
        layer, action, objs, score = r.layer, r.action, r.objects, r.score
        hits = ",".join(r.hits[:3])
    except Exception:
        layer, action, objs, score, hits = "ERR", "", [], 0, "路由异常"

    try:
        body, name = cb.local_compose_body(t)
        blen = len(body or "")
    except Exception:
        blen, name = -1, "EXC"
        stat["exc"] += 1

    ok = blen >= 400
    if ok:
        stat["body_ok"] += 1
        stat["len_min"] = min(stat["len_min"], blen)
        stat["len_max"] = max(stat["len_max"], blen)
    elif blen == 0:
        stat["body_empty"] += 1

    stat["layer"][layer] = stat["layer"].get(layer, 0) + 1
    stat["action"][action or "-"] = stat["action"].get(action or "-", 0) + 1

    rows.append("| %s | %-4s | %-7s | %-19s | %5d | %-5s | %s |"
                % ("PASS" if ok else "FAIL", layer, action or "-",
                   ",".join(objs) or "-", blen, name or "-", t))

head = ["| 结果 | 层 | 动作 | 对象 | 字数 | 目标物 | 输入 |",
        "|---|---|---|---|---|---|---|"]
tail = ["",
        "总数 %d ｜ 出正文 %d ｜ 空返回 %d ｜ 异常 %d" %
        (stat["total"], stat["body_ok"], stat["body_empty"], stat["exc"]),
        "篇幅区间 %d ~ %d 字" % (stat["len_min"], stat["len_max"]),
        "层分布 " + json.dumps(stat["layer"], ensure_ascii=False),
        "动作分布 " + json.dumps(stat["action"], ensure_ascii=False)]

io.open("_test_report.md", "w", encoding="utf-8").write("\n".join(head + rows + tail))
print("cases=%d ok=%d empty=%d exc=%d" %
      (stat["total"], stat["body_ok"], stat["body_empty"], stat["exc"]))
