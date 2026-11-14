#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""semantic_serve.py — 本地语义检索服务（给 relay 用）

为什么起一个独立服务
--------------------
软件（Python）已经有 semantic_router，但 relay 是 Node。
两边必须用**同一套判断**，否则又会出现
「面板说命中 A、新会话返回 B」这种双链路口径打架。

模型加载要 17–18 s，绝不能每次请求都重来。
所以起一个常驻 HTTP 服务，模型只加载一次，之后每次查询 ~15 ms。

接口
----
POST /search   {"query": "...", "topk": 3}
  → {"hits":[{"key":"...","score":0.78}], "lib":"...", "n":35}

GET  /health
  → {"ok":true, "n":35, "model":"bge-small-zh", "warm":true}

GET  /body?key=xxx
  → 纯文本（条目正文），找不到 404

只监听 127.0.0.1，不对外。

启动
----
  python semantic_serve.py            # 前台，端口 17802
  python semantic_serve.py --port 17802
"""

import argparse
import io
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import semantic_router as sr  # noqa: E402

LIB_DIR = os.path.join(os.path.expanduser("~"), ".workbuddy", "coffee-lib")

_warm_lock = threading.Lock()
_warm_done = threading.Event()


def _warm():
    with _warm_lock:
        if _warm_done.is_set():
            return
        try:
            if not sr._try_cache(LIB_DIR):
                sr.build_index(LIB_DIR)
        except Exception as e:
            sys.stderr.write("[semantic-serve] 预热失败：%s\n" % e)
        _warm_done.set()


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        pass  # 不刷屏

    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _text(self, s, code=200):
        b = str(s).encode("utf-8")
        self.send_response(code)
        self.send_header("content-type", "text/plain; charset=utf-8")
        self.send_header("content-length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        p = self.path.split("?")[0]
        qs = {}
        if "?" in self.path:
            for kv in self.path.split("?", 1)[1].split("&"):
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    from urllib.parse import unquote
                    qs[k] = unquote(v)
        if p == "/health":
            return self._json({
                "ok": True,
                "n": len(sr._state.get("keys") or []),
                "model": "bge-small-zh-v1.5",
                "warm": _warm_done.is_set(),
                "lib": LIB_DIR,
                "threshold": sr.THRESHOLD,
            })
        if p == "/body":
            k = qs.get("key", "")
            if not k:
                return self._text("missing key", 400)
            try:
                idx = json.load(io.open(os.path.join(LIB_DIR, "index.json"), encoding="utf-8"))
                meta = (idx.get("topics") or {}).get(k) or {}
                fp = os.path.join(LIB_DIR, meta.get("file") or "")
                if os.path.exists(fp):
                    return self._text(io.open(fp, encoding="utf-8", errors="replace").read())
            except Exception as e:
                return self._text("err %s" % e, 500)
            return self._text("not found", 404)
        return self._json({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        p = self.path.split("?")[0]
        if p != "/search":
            return self._json({"ok": False, "error": "not found"}, 404)
        try:
            n = int(self.headers.get("content-length") or 0)
            raw = self.rfile.read(n) if n else b"{}"
            req = json.loads(raw.decode("utf-8") or "{}")
        except Exception as e:
            return self._json({"ok": False, "error": "bad json %s" % e}, 400)
        q = str(req.get("query") or "").strip()
        topk = int(req.get("topk") or 3)
        if not q:
            return self._json({"ok": False, "hits": []}, 200)
        # 预热没完就先等一下，最多 30 s（第一次请求时才发生）
        if not _warm_done.is_set():
            _warm_done.wait(30)
        hits = sr.search(LIB_DIR, q, topk=topk)
        return self._json({
            "ok": True,
            "query": q,
            "hits": [{"key": k, "score": s} for k, s in hits],
            "n": len(sr._state.get("keys") or []),
        })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=17802)
    ap.add_argument("--host", default="127.0.0.1")
    a = ap.parse_args()
    threading.Thread(target=_warm, daemon=True, name="warm").start()
    srv = ThreadingHTTPServer((a.host, a.port), H)
    sys.stderr.write("[semantic-serve] listening on http://%s:%d  lib=%s\n"
                     % (a.host, a.port, LIB_DIR))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
