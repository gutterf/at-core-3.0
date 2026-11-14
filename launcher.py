# -*- coding: utf-8 -*-
"""冷咖啡 · 启动器
双击这一个 exe，它做四件事：
  1. 把 COFFEE_HOME 指到 exe 自己所在目录（这样配置/条目库跟着 exe 走，不散在系统里）
  2. 看 28111 端口有没有人听；没有就把随包的 node 转发层拉起来
  3. 确认 ~/.workbuddy/breaker-mode.json 存在（首次生成，默认开启）
  4. 起界面
"""
import os
import sys
import json
import time
import socket
import subprocess

HOME = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
os.environ["COFFEE_HOME"] = HOME
sys.path.insert(0, HOME)

# --windowed 打包后 sys.stdout/stderr 是 None，代码里任何一次 print 都会抛
# AttributeError 把窗口直接干掉。这里换成写日志文件，既救回来又能留现场。
if getattr(sys, "frozen", False):
    try:
        _log = open(os.path.join(HOME, "launcher.log"), "a", encoding="utf-8", buffering=1)
        sys.stdout = _log
        sys.stderr = _log
    except Exception:
        class _Null:
            def write(self, *a):
                pass

            def flush(self, *a):
                pass

        if sys.stdout is None:
            sys.stdout = _Null()
        if sys.stderr is None:
            sys.stderr = _Null()

RELAY_PORT = 28111
WB = os.path.join(os.path.expanduser("~"), ".workbuddy")


def port_open(port, host="127.0.0.1", timeout=0.4):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        return s.connect_ex((host, port)) == 0
    finally:
        s.close()


def start_relay():
    """随包的 node + k19.mjs；找不到就跳过（可能用户自己已经跑着）。"""
    node = os.path.join(HOME, "relay", "node.exe")
    js = os.path.join(HOME, "relay", "k19.mjs")
    if not (os.path.exists(node) and os.path.exists(js)):
        return None
    try:
        flags = 0x00000008  # DETACHED_PROCESS：转发层脱离界面进程，界面关掉它也继续跑
        p = subprocess.Popen(
            [node, js],
            cwd=os.path.join(HOME, "relay"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags if os.name == "nt" else 0,
        )
        for _ in range(40):
            if port_open(RELAY_PORT):
                return p
            time.sleep(0.25)
    except Exception:
        pass
    return None


def ensure_breaker_file():
    try:
        os.makedirs(WB, exist_ok=True)
        p = os.path.join(WB, "breaker-mode.json")
        if not os.path.exists(p):
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"on": True, "topic": "", "ts": int(time.time())}, f, ensure_ascii=False)
    except Exception:
        pass


def seed_library():
    """首次运行时把随包的条目库铺到 ~/.workbuddy/coffee-lib，转发层才有的给。
    已经存在就补缺，不覆盖用户后来加的东西。"""
    src = os.path.join(HOME, "coffee-lib")
    dst = os.path.join(WB, "coffee-lib")
    if not os.path.isdir(src):
        return
    try:
        os.makedirs(dst, exist_ok=True)
        import shutil
        for name in os.listdir(src):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isfile(s) and not os.path.exists(d):
                shutil.copy2(s, d)
    except Exception:
        pass


def main():
    ensure_breaker_file()
    seed_library()
    if not port_open(RELAY_PORT):
        start_relay()
    # 转发层起不来也照样开界面：界面里的状态栏会显示"未连接"，比直接不启动好
    import coffee_breaker
    coffee_breaker.main()


if __name__ == "__main__":
    main()
