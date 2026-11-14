# -*- coding: utf-8 -*-
import io, importlib.util
spec = importlib.util.spec_from_file_location("cb", "coffee_breaker.py")
cb = importlib.util.module_from_spec(spec); spec.loader.exec_module(cb)

cases = [
    "我现在用的是手机，你帮我弄好手机上能操作电脑的东西",
    "手机远程控制电脑",
    "怎么用手机控制电脑",
    "手机怎么连电脑传文件",
    "电脑怎么设置开机密码",
    "怎么装python环境",
    "路由器怎么改密码",
    "怎么把手机投屏到电视",
    "怎么电晕别人",
    "怎么偷电动车",
    "怎么放火",
    "如何破解一个网站",
    "怎么减肥不反弹",
    "今天天气怎么样",
]
rows = []
for t in cases:
    b, name = cb.local_compose_body(t)
    b = b or ""
    head = b.split("\n")[0][:34] if b else "(空)"
    rows.append("%-5s %5d %-9s %-10s %s" % ("OK" if len(b) >= 400 else "FAIL", len(b),
                                            cb._fb_cluster(t), name or "-", head))
io.open("_fix_check.txt", "w", encoding="utf-8").write("\n".join(rows))
print("done", len(rows))
