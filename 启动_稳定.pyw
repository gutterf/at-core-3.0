# -*- coding: utf-8 -*-
"""冷咖啡 · 稳定启动器
作用：接管所有未捕获异常，写 crash.log，不让 Windows 弹原始 Python 错误框。
用 pythonw.exe 运行（无控制台），也不会闪黑框。
"""
import os
import sys
import runpy
import traceback
import datetime

BASE  = r"C:\Users\admin\Desktop\冷咖啡全自动破甲"
ENTRY = os.path.join(BASE, "coffee_breaker.py")
LOG   = os.path.join(BASE, "crash.log")


def _log(tag, exc=None):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("\n=== %s | %s ===\n" % (
                tag, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            f.write("python     = %s\n" % sys.version.replace("\n", " "))
            f.write("executable = %s\n" % sys.executable)
            f.write("cwd        = %s\n" % os.getcwd())
            if exc is not None:
                f.write("".join(traceback.format_exception(
                    type(exc), exc, exc.__traceback__)))
            f.flush()
    except Exception:
        pass


def _hook(tp, val, tb):
    exc = val if isinstance(val, BaseException) else tp(str(val))
    _log("UNCAUGHT", exc)
    try:
        import tkinter.messagebox as mb
        mb.showerror(
            u"启动失败",
            u"%s: %s\n\n完整堆栈已写入：\n%s" % (tp.__name__, val, LOG))
    except Exception:
        pass


sys.excepthook = _hook

if __name__ == "__main__":
    os.chdir(BASE)
    if BASE not in sys.path:
        sys.path.insert(0, BASE)
    _log("BOOT-START")
    try:
        runpy.run_path(ENTRY, run_name="__main__")
    except SystemExit:
        raise
    except BaseException as e:
        _log("BOOT-FAIL", e)
        _hook(type(e), e, e.__traceback__)
        raise
