# -*- coding: utf-8 -*-
"""破甲注入器 · 启动页层（Gate）

结构：
  启动页 = 一个覆盖在主窗口上的 Toplevel（无边框，尺寸位置实时跟随主窗口）
  点「破甲注入器」按钮 -> 销毁 Toplevel -> 主界面照常显示
  主界面左上角挂一个圆形 ‹ 返回按钮 -> 重新弹出 Toplevel

关键：不动主界面任何控件的父容器，只做显隐，避免布局塌陷。
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

from PIL import Image, ImageDraw, ImageFilter, ImageTk

from glass_ui import BG, ACCENT_HEX, UI_FONT, build_wallpaper

GATE_BG = "#05070C"
RING = (62, 232, 200)

# 与桌面图标一致：48 x 48
ICON_PX = 48


# ---------------------------------------------------------------- 图标
def draw_breaker_icon(size=ICON_PX):
    """破甲图标：盾形 + 闪电裂纹 + 中心冲击点，48px 与桌面图标同尺寸。"""
    ss = 8
    W = size * ss
    img = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = int(W * 0.06)
    d.ellipse((pad, pad, W - pad, W - pad), outline=(RING[0], RING[1], RING[2], 70),
              width=max(1, int(W * 0.012)))

    cx = W / 2
    top, bot = W * 0.18, W * 0.82
    left, right = W * 0.24, W * 0.76
    shield = [(cx, top), (right, top + W * 0.09), (right, W * 0.52),
              (cx, bot), (left, W * 0.52), (left, top + W * 0.09)]
    d.polygon(shield, fill=(9, 24, 28, 238),
              outline=(RING[0], RING[1], RING[2], 240), width=max(2, int(W * 0.020)))

    lw = max(2, int(W * 0.026))
    bolt = [(cx, W * 0.28), (cx - W * 0.050, W * 0.43), (cx + W * 0.024, W * 0.47),
            (cx - W * 0.034, W * 0.61), (cx + W * 0.012, W * 0.74)]
    d.line(bolt, fill=(255, 255, 255, 250), width=lw, joint="curve")
    d.line(bolt, fill=(RING[0], RING[1], RING[2], 255), width=max(1, lw // 2), joint="curve")
    d.line([(cx - W * 0.050, W * 0.43), (left + W * 0.050, W * 0.505)],
           fill=(RING[0], RING[1], RING[2], 205), width=max(1, lw // 2))
    d.line([(cx + W * 0.024, W * 0.47), (right - W * 0.048, W * 0.415)],
           fill=(RING[0], RING[1], RING[2], 205), width=max(1, lw // 2))

    r = W * 0.038
    d.ellipse((cx - r, W * 0.47 - r, cx + r, W * 0.47 + r), fill=(255, 255, 255, 252))
    return img.resize((size, size), Image.Resampling.LANCZOS)


def icon_with_glow(size=ICON_PX, pad=10):
    canvas = size + pad * 2
    art = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    glow = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse((pad - 1, pad - 1, pad + size, pad + size),
               outline=(RING[0], RING[1], RING[2], 155), width=max(2, size // 22))
    glow = glow.filter(ImageFilter.GaussianBlur(size // 20))
    art.alpha_composite(glow)
    art.alpha_composite(draw_breaker_icon(size), (pad, pad))
    return art


# ---------------------------------------------------------------- 启动页窗口
class GateWindow:
    """覆盖主窗口的启动页。"""

    def __init__(self, root, on_enter):
        self.root = root
        self.on_enter = on_enter
        self.top = tk.Toplevel(root)
        self.top.withdraw()
        self.top.overrideredirect(True)
        self.top.configure(bg=GATE_BG)
        self.top.attributes("-topmost", False)

        self.canvas = tk.Canvas(self.top, bg=GATE_BG, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)

        self._photo_wp = None
        self._photo_icon = None
        self._photo_btn = None
        self._photo_btn_hover = None
        self._size = (0, 0)
        self._zone = None
        self._hover = False
        self._busy = False
        self._follow_job = None

        self.canvas.bind("<Configure>", self._on_resize)
        self.top.bind("<Configure>", self._on_top_configure)
        self.canvas.bind("<Motion>", self._on_motion)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<Leave>", lambda e: self._set_hover(False))
        self.top.bind("<Escape>", lambda e: self.close())

    # -- 跟随主窗口 --
    def _follow(self):
        if not self.top.winfo_exists():
            return
        try:
            x = self.root.winfo_rootx()
            y = self.root.winfo_rooty()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            tw, th = self.top.winfo_width(), self.top.winfo_height()
            if (self.top.winfo_x(), self.top.winfo_y()) != (x, y) or (tw, th) != (w, h):
                self.top.geometry("%dx%d+%d+%d" % (w, h, x, y))
            # 尺寸没算对就补一次重绘（Toplevel 首次显示时 winfo 还是 1）
            want = (w, h)
            if w > 80 and h > 80 and self._size != want:
                self._size = want
                self.redraw()
        except Exception:
            pass
        self._follow_job = self.top.after(80, self._follow)

    def open(self):
        self._busy = False
        self._hover = False
        try:
            self.root.update_idletasks()
        except Exception:
            pass
        try:
            w = max(640, self.root.winfo_width())
            h = max(480, self.root.winfo_height())
            x = self.root.winfo_rootx()
            y = self.root.winfo_rooty()
            self.top.geometry("%dx%d+%d+%d" % (w, h, x, y))
        except Exception:
            pass
        self.top.deiconify()
        self.top.lift()

        # 关键：Toplevel 刚显示时 winfo_width 仍是 1，
        # 必须 update_idletasks 拿到真实尺寸，再用 geometry 期望值兜底
        self._want = None
        try:
            self.root.update_idletasks()
            self.top.update_idletasks()
        except Exception:
            pass
        real_w, real_h = self.top.winfo_width(), self.top.winfo_height()
        if real_w <= 1 or real_h <= 1:
            real_w, real_h = w, h
        self._size = (int(real_w), int(real_h))
        self.redraw()

        if self._follow_job:
            try:
                self.top.after_cancel(self._follow_job)
            except Exception:
                pass
        self._follow()

    def close(self):
        if self._follow_job:
            try:
                self.top.after_cancel(self._follow_job)
            except Exception:
                pass
            self._follow_job = None
        try:
            self.top.withdraw()
            self.top.destroy()
        except Exception:
            pass

    # -- 绘制 --
    def _on_top_configure(self, event):
        if event.widget is not self.top:
            return
        if (event.width, event.height) == self._size:
            return
        if event.width < 80 or event.height < 80:
            return
        self._size = (event.width, event.height)
        self.redraw()

    def _on_resize(self, event):
        if (event.width, event.height) == self._size:
            return
        if event.width < 80 or event.height < 80:
            return
        self._size = (event.width, event.height)
        self.redraw()

    def redraw(self):
        w, h = self._size
        if w < 80 or h < 80:
            return
        c = self.canvas
        c.delete("all")

        wp = build_wallpaper(w, h).convert("RGB").point(lambda v: int(v * 0.60))
        vig = Image.new("L", (w, h), 0)
        ImageDraw.Draw(vig).ellipse((-w * 0.32, -h * 0.42, w * 1.32, h * 1.42), fill=255)
        vig = vig.filter(ImageFilter.GaussianBlur(max(20, int(min(w, h) * 0.10))))
        wp = Image.composite(wp, Image.new("RGB", (w, h), (3, 5, 9)), vig)
        self._photo_wp = ImageTk.PhotoImage(wp)
        c.create_image(0, 0, anchor="nw", image=self._photo_wp, tags="wp")

        cx = w / 2
        icon_cy = h * 0.40

        art = icon_with_glow(ICON_PX)
        self._photo_icon = ImageTk.PhotoImage(art)
        c.create_image(cx, icon_cy, image=self._photo_icon, tags="icon")

        f1 = tkfont.Font(family=UI_FONT, size=17, weight="bold")
        ty = icon_cy + ICON_PX / 2 + 28
        a, b = "破甲", "注入器"
        wa, wb = f1.measure(a), f1.measure(b)
        x0 = cx - (wa + wb) / 2
        c.create_text(x0, ty, anchor="nw", text=a, fill="#F3F8FC", font=f1, tags="title")
        c.create_text(x0 + wa, ty, anchor="nw", text=b, fill=ACCENT_HEX, font=f1, tags="title")

        c.create_text(cx, ty + f1.metrics("linespace") + 6,
                      text="B R E A K   / /   O P E N",
                      fill="#4A5C70", font=("Segoe UI", 7), tags="sub")

        bw, bh = ICON_PX * 3, 34
        by = ty + f1.metrics("linespace") + 30
        self._zone = (cx - bw / 2, by, bw, bh)

        c.create_text(cx, by + bh + 18, text="冷咖啡 · 全自动破甲",
                      fill="#2A3B4C", font=(UI_FONT, 7), tags="foot")
        self._draw_button()

    def _button_image(self, bw, bh, hover):
        ss = 3
        img = Image.new("RGBA", (bw * ss, bh * ss), (0, 0, 0, 0))
        r = int(bh * ss * 0.30)
        top = (86, 248, 216, 255) if hover else (72, 238, 206, 255)
        bot = (26, 168, 148, 255) if hover else (18, 148, 130, 255)
        grad = Image.new("RGBA", (bw * ss, bh * ss))
        gd = ImageDraw.Draw(grad)
        for y in range(bh * ss):
            t = y / max(1, bh * ss - 1)
            gd.line([(0, y), (bw * ss, y)],
                    fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,))
        mask = Image.new("L", (bw * ss, bh * ss), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw * ss - 1, bh * ss - 1), radius=r, fill=255)
        img.paste(grad, (0, 0), mask)
        ImageDraw.Draw(img).rounded_rectangle((0, 0, bw * ss - 1, bh * ss - 1),
                                              radius=r, outline=(200, 255, 244, 230),
                                              width=max(2, ss))
        return ImageTk.PhotoImage(img.resize((bw, bh), Image.Resampling.LANCZOS))

    def _draw_button(self):
        c = self.canvas
        c.delete("btn")
        if not self._zone:
            return
        x, y, bw, bh = self._zone
        photo = self._button_image(int(bw), int(bh), self._hover)
        if self._hover:
            self._photo_btn_hover = photo
        else:
            self._photo_btn = photo
        cx = x + bw / 2
        c.create_image(cx, y + bh / 2, image=photo, tags="btn")
        c.create_text(cx, y + bh / 2, text="破甲注入器", fill="#04211C",
                      font=(UI_FONT, 10, "bold"), tags="btn")

    def _hit(self, x, y):
        if not self._zone:
            return False
        bx, by, bw, bh = self._zone
        return bx <= x <= bx + bw and by <= y <= by + bh

    def _set_hover(self, on):
        if self._hover == on:
            return
        self._hover = on
        try:
            self.canvas.configure(cursor="hand2" if on else "")
        except Exception:
            pass
        self._draw_button()

    def _on_motion(self, event):
        self._set_hover(self._hit(event.x, event.y))

    def _on_click(self, event):
        if self._hit(event.x, event.y):
            self.enter()

    def enter(self):
        if self._busy:
            return
        self._busy = True
        self.on_enter()


# ---------------------------------------------------------------- 路由
class PageRouter:
    def __init__(self, root):
        self.root = root
        self.gate = None
        self.on_show = None
        self._back_btn = None
        self.main_title = "冷咖啡 · 全自动破甲"

    def show_gate(self):
        try:
            self.root.title(self.main_title)
        except Exception:
            pass
        if self.gate is None:
            self.gate = GateWindow(self.root, self._enter_main)
        self.gate.open()

    def _enter_main(self):
        if self.gate is not None:
            self.gate.close()
            self.gate = None
        self._install_back_button()
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.root.title(self.main_title)
        except Exception:
            pass
        if callable(self.on_show):
            try:
                self.on_show()
            except Exception:
                pass

    def _install_back_button(self):
        if self._back_btn is not None:
            try:
                if self._back_btn.winfo_exists():
                    tk.Misc.lift(self._back_btn)
                    return
            except Exception:
                pass
        # 30 x 30，塞在左上角边距里，不压住 COLD BREW 那行
        btn = tk.Canvas(self.root, width=30, height=30, bg=BG,
                        highlightthickness=0, bd=0, cursor="hand2")
        btn.place(x=6, y=8)
        # Canvas.lift 是 tag_raise，提升窗口要用 Misc.lift
        tk.Misc.lift(btn)

        def paint(hover=False):
            btn.delete("all")
            fill = "#0C151E" if not hover else "#16333A"
            line = "#1E2E3C" if not hover else ACCENT_HEX
            btn.create_oval(2, 2, 27, 27, fill=fill, outline=line, width=1)
            btn.create_line(18, 10, 11, 15, 18, 20,
                            fill=ACCENT_HEX if hover else "#9FB3C4",
                            width=2, capstyle="round", joinstyle="round")

        paint(False)
        btn.bind("<Enter>", lambda e: paint(True))
        btn.bind("<Leave>", lambda e: paint(False))
        btn.bind("<Button-1>", lambda e: self.show_gate())
        self._back_btn = btn


_ROUTER = {}


def install(root):
    router = PageRouter(root)
    _ROUTER["r"] = router
    return router


def start_with_gate(root):
    router = _ROUTER.get("r")
    if router is None:
        router = install(root)
    router.show_gate()


def set_main_title(title):
    router = _ROUTER.get("r")
    if router is not None:
        router.main_title = title
