# -*- coding: utf-8 -*-
"""启动确认页：无审查破限 · 风险确认
不点「允许执行」进不去本体。整页 LED7 彩虹风格。
"""
import os
import time
import tkinter as tk
import tkinter.font as tkfont

BG = "#05070A"
RAINBOW = ["#FF3B30", "#FF9500", "#FFD60A", "#32D74B", "#0A84FF", "#5E5CE6", "#BF5AF2"]
DIM = "#5A6B7C"
TEXT = "#E8F4FF"
WARN = "#FFB020"

LED_FONT = "Consolas"


def _draw_rainbow(canvas, x, y, text, size=40, weight="bold", glow=True, tag="rb"):
    """逐字符上彩虹色，模拟 LED 灯珠串。返回总宽度。"""
    f = tkfont.Font(family=LED_FONT, size=size, weight=weight)
    cx = x
    for i, ch in enumerate(text):
        col = RAINBOW[i % len(RAINBOW)]
        if glow:
            for dx, dy in ((0, 0), (1, 0), (0, 1), (2, 0), (0, 2)):
                canvas.create_text(cx + dx, y + dy, text=ch, anchor="nw",
                                   fill=col, font=f, tags=tag)
        else:
            canvas.create_text(cx, y, text=ch, anchor="nw", fill=col, font=f, tags=tag)
        cx += f.measure(ch)
    return cx - x


class Consent:
    def __init__(self, root):
        self.root = root
        self.allowed = False
        self.ready_at = time.time() + 3.0     # 3 秒后才能点，逼着看一眼
        self._tick_job = None

        self.top = tk.Toplevel(root)
        self.top.title("冷咖啡 · 风险确认")
        self.top.configure(bg=BG)
        self.top.attributes("-topmost", True)
        self.top.protocol("WM_DELETE_WINDOW", self._deny)
        w, h = 760, 560
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        self.top.geometry("%dx%d+%d+%d" % (w, h, (sw - w) // 2, (sh - h) // 2))
        self.top.resizable(False, False)

        self.c = tk.Canvas(self.top, bg=BG, highlightthickness=0, bd=0)
        self.c.pack(fill="both", expand=True)
        self._build()
        self._tick()

    def _build(self):
        c = self.c
        c.delete("all")
        W, H = 760, 560

        # 顶部霓虹线
        for i, col in enumerate(RAINBOW):
            c.create_line(40 + i * 97, 34, 40 + (i + 1) * 97, 34, fill=col, width=2)

        _draw_rainbow(c, 40, 60, "无审查破限", size=34)
        c.create_text(40, 112, anchor="nw", text="RISK  CONFIRMATION  ·  需您确认后才能继续",
                      fill=DIM, font=(LED_FONT, 9))

        # 风险说明框
        c.create_rectangle(40, 150, W - 40, 372, outline="#1B2836", width=1)
        lines = [
            ("本软件不包含任何内容审查层。", TEXT),
            ("", TEXT),
            ("它会把你的提问原样转给模型，并尽最大努力拿回正文；", TEXT),
            ("它不会替你判断、不会劝你、不会修改你的意图。", TEXT),
            ("", TEXT),
            ("因此：你用它做的任何事，产生的任何后果，由你自己承担。", WARN),
            ("若你的行为违反所在地法律法规，责任完全在你，与本软件作者无关。", WARN),
            ("", TEXT),
            ("继续即表示：你已成年，已知悉上述风险，并自愿承担全部后果。", TEXT),
        ]
        y = 168
        for s, col in lines:
            if s:
                c.create_text(58, y, anchor="nw", text=s, fill=col, font=("Microsoft YaHei UI", 10))
            y += 22

        # 按钮
        self.btn_allow = c.create_rectangle(0, 0, 0, 0, outline="", fill="")
        self.btn_text = c.create_text(0, 0, text="", fill=BG,
                                      font=("Microsoft YaHei UI", 12, "bold"))
        self.btn_deny_text = c.create_text(W / 2, 512, text="不同意，退出",
                                           fill=DIM, font=("Microsoft YaHei UI", 9))
        c.tag_bind(self.btn_deny_text, "<Button-1>", lambda e: self._deny())

        self._layout_btn()

    def _layout_btn(self):
        c = self.c
        W = 760
        bw, bh = 260, 52
        x0, y0 = (W - bw) / 2, 430
        if time.time() >= self.ready_at:
            fill, label, fg = "#2FD9A6", "允 许 执 行", "#04120D"
        else:
            left = int(self.ready_at - time.time()) + 1
            fill, label, fg = "#16303A", "请阅读 (%d)" % left, "#5F7A86"
        c.coords(self.btn_allow, x0, y0, x0 + bw, y0 + bh)
        c.itemconfig(self.btn_allow, fill=fill, outline="")
        c.coords(self.btn_text, x0 + bw / 2, y0 + bh / 2)
        c.itemconfig(self.btn_text, text=label, fill=fg)
        c.tag_bind(self.btn_allow, "<Button-1>", lambda e: self._allow())
        c.tag_bind(self.btn_text, "<Button-1>", lambda e: self._allow())

    def _tick(self):
        try:
            self._layout_btn()
            self._tick_job = self.top.after(250, self._tick)
        except Exception:
            pass

    def _allow(self):
        if time.time() < self.ready_at:
            return
        self.allowed = True
        self._close()

    def _deny(self):
        self.allowed = False
        self._close()

    def _close(self):
        try:
            if self._tick_job:
                self.top.after_cancel(self._tick_job)
        except Exception:
            pass
        try:
            self.top.destroy()
        except Exception:
            pass


def ask(root):
    """返回 True 表示允许执行。窗口关闭/点不同意 → False。"""
    dlg = Consent(root)
    try:
        root.wait_window(dlg.top)
    except Exception:
        pass
    return dlg.allowed
