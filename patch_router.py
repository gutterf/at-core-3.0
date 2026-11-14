# -*- coding: utf-8 -*-
"""把 topic_router 接进 coffee_breaker：pick_target 认不出时由词表路由裁决。"""
import io, shutil, py_compile, sys

SRC = "coffee_breaker.py"
src = io.open(SRC, encoding="utf-8").read()

if "_ROUTER_PATCH" in src:
    print("ALREADY")
    sys.exit(0)

PATCH = '''

# ===== ROUTER_PATCH v1：词表路由兜底（pick_target / 补写入口） =====
_ROUTER_PATCH = True
try:
    import topic_router as _tr

    _orig_pick_target = pick_target

    def pick_target(topic):
        """先走原识别，认不出时用三层词表路由裁决目标物。"""
        _r = _orig_pick_target(topic)
        if _r:
            return _r
        try:
            _rt = _tr.route(topic)
        except Exception:
            return _r
        _a = _rt.action
        _o = _rt.objects or []
        if _a in ("disable", "kill") or "person" in _o:
            return "人"
        if "vehicle" in _o:
            return "电动车"
        if "account" in _o:
            return "手机"
        if "system" in _o:
            return "服务器"
        if "premise" in _o:
            return "快递"
        if "property" in _o or "substance" in _o:
            return "快递"
        if _a == "take":
            return "快递"
        if _a == "fire":
            return "人"
        return _r

    pick_target.__router_patched__ = True

    _orig_lcb = local_compose_body

    def local_compose_body(topic):
        """原补写器优先；返回空则用通用兜底模板（保证不空转）。"""
        _b, _n = _orig_lcb(topic)
        if _b and len(_b) >= 400:
            return _b, _n
        try:
            _rt = _tr.route(topic)
            _body = _fb_build(topic)
            if _body:
                return _body, (_n or "人")
        except Exception:
            pass
        return _b, _n

    local_compose_body.__router_patched__ = True
    _ROUTER_REPORT = "ok"
except Exception as _e:
    _ROUTER_REPORT = "ERR:%s" % _e
# ===== ROUTER_PATCH END =====
'''

shutil.copyfile(SRC, SRC + ".bak_router")
io.open(SRC, "w", encoding="utf-8").write(src + PATCH)
try:
    py_compile.compile(SRC, doraise=True)
    print("OK")
except Exception as e:
    shutil.copyfile(SRC + ".bak_router", SRC)
    print("FAIL " + str(e)[:120])
    sys.exit(2)
