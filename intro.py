# -*- coding: utf-8 -*-
"""Cinematic intro / welcome overlay for 冷咖啡 · 全自动破甲."""
from __future__ import annotations

import math
import os
import random
import time
import tkinter as tk
import tkinter.font as tkfont

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageTk

import glass_ui as gui

FONT_PATH = r"C:\Windows\Fonts\msyhbd.ttc"
BG = "#05070C"
DARK = "#0A1018"
WHITE = "#F2FBF8"
MINT = "#6FF3D6"
DIM = "#6E8798"


def _ease_out(p):
    p = max(0.0, min(1.0, p))
    return 1.0 - (1.0 - p) ** 3


def _ease_in(p):
    p = max(0.0, min(1.0, p))
    return p ** 3


def _ease_in_out(p):
    p = max(0.0, min(1.0, p))
    return p * p * (3 - 2 * p)


def _ease_out_back(p):
    p = max(0.0, min(1.0, p))
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (p - 1.0) ** 3 + c1 * (p - 1.0) ** 2


def _seg(t, start, dur):
    if dur <= 0:
        return 1.0
    return max(0.0, min(1.0, (t - start) / dur))


def _alpha_frames(img, n=10):
    frames = []
    base = img.convert("RGBA")
    a0 = base.getchannel("A")
    for i in range(n):
        f = base.copy()
        f.putalpha(a0.point(lambda v, k=i / (n - 1.0): int(v * k)))
        frames.append(ImageTk.PhotoImage(f))
    return frames


def _scaled_frames(img, sizes, n=10):
    frames = []
    for i in range(n):
        p = i / (n - 1.0)
        s = sizes[0] + (sizes[1] - sizes[0]) * _ease_out(p)
        w = max(1, int(img.width * s))
        h = max(1, int(img.height * s))
        f = img.resize((w, h), Image.Resampling.LANCZOS)
        a = f.getchannel("A").point(lambda v, k=p: int(v * k))
        f.putalpha(a)
        frames.append(ImageTk.PhotoImage(f))
    return frames


def _shield_base(size=96):
    s = 4
    S = size * s
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(0.50, 0.07), (0.80, 0.20), (0.77, 0.56), (0.50, 0.91), (0.23, 0.56), (0.20, 0.20)]
    poly = [(x * S, y * S) for x, y in pts]
    d.polygon(poly, fill=(7, 18, 22, 216))
    d.line(poly + [poly[0]], fill=(104, 246, 216, 255), width=int(3.0 * s), joint="curve")
    bolt = [(0.545, 0.26), (0.395, 0.525), (0.492, 0.525), (0.445, 0.735), (0.625, 0.445), (0.520, 0.445)]
    d.polygon([(x * S, y * S) for x, y in bolt], fill=(160, 255, 236, 255))
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.line(poly + [poly[0]], fill=(90, 240, 210, 210), width=int(7 * s), joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(9 * s))
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(img)
    return out.resize((size, size), Image.Resampling.LANCZOS)


def _text_glow(text, px, color, blur):
    try:
        font = ImageFont.truetype(FONT_PATH, px)
    except Exception:
        font = ImageFont.load_default()
    bbox = font.getbbox(text)
    pad = blur * 2 + 8
    w = max(2, bbox[2] - bbox[0] + pad * 2)
    h = max(2, bbox[3] - bbox[1] + pad * 2)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((pad - bbox[0], pad - bbox[1]), text, font=font, fill=color)
    return img.filter(ImageFilter.GaussianBlur(blur))


def _button_image(w, h, state="normal"):
    W, H = w + 90, h + 90
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_a = {"normal": 88, "hover": 130, "press": 60}[state]
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle(
        (45, 45, 45 + w, 45 + h), radius=h // 2, fill=(86, 240, 210, glow_a))
    glow = glow.filter(ImageFilter.GaussianBlur(22))
    img.alpha_composite(glow)

    top = (108, 247, 219) if state != "press" else (72, 208, 182)
    bot = (18, 164, 141) if state != "press" else (12, 122, 105)
    g = Image.linear_gradient("L").resize((w, h), Image.Resampling.BILINEAR)
    t = Image.new("RGB", (w, h), top)
    b = Image.new("RGB", (w, h), bot)
    grad = Image.composite(b, t, g).convert("RGBA")
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=255)
    grad.putalpha(mask)
    sheen = gui._vgrad((w, h), (255, 255, 255), 46, 0, 0.0, 0.45)
    grad = Image.alpha_composite(grad, sheen)
    bd = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(bd).rounded_rectangle((1, 1, w - 2, h - 2), radius=h // 2,
                                         outline=(220, 255, 246, 150), width=2)
    grad = Image.alpha_composite(grad, bd)
    ox = (W - w) // 2
    oy = (H - h) // 2
    if state == "press":
        grad = grad.resize((w - 6, h - 6), Image.Resampling.LANCZOS)
        ox += 3
        oy += 3
    img.alpha_composite(grad, (ox, oy))
    return img


class IntroOverlay(tk.Canvas):
    def __init__(self, root, shell, on_finish=None):
        super().__init__(root, bg=BG, highlightthickness=0, bd=0)
        self.root = root
        self.shell = shell
        self.on_finish = on_finish
        self.phase = "landing"
        self.t0 = time.time()
        self.welcome_t0 = 0.0
        self.exiting = False
        self.exit_t0 = 0.0
        self.exit_dur = 0.55
        self._job = None
        self._resize_job = None
        self.place(x=0, y=0, relwidth=1, relheight=1)
        self.tk.call("raise", str(self))
        self.bind("<Configure>", self._on_resize)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Button-1>", self._on_down)
        self.bind("<ButtonRelease-1>", self._on_up)
        self._esc_id = root.bind("<Escape>", self._on_esc, add="+")
        self._items = {}
        self._photos = {}
        self._particles = []
        self._rings = []
        self._welcome_chars = []
        self._hover = False
        self._down = False
        self._locked = os.environ.get("LCS_INTRO_LOCK") == "1"
        self._build()
        self._dark_job = self.root.after(260, self._keep_dark)
        self._tick()

    # ---------------------------------------------------------- assets
    def _keep_dark(self):
        if not self.winfo_exists():
            return
        try:
            gui.enable_dark_title(self.root)
        except Exception:
            pass
        self._dark_job = self.root.after(700, self._keep_dark)

    def _on_resize(self, e):
        if self._resize_job:
            try:
                self.root.after_cancel(self._resize_job)
            except Exception:
                pass
        self._resize_job = self.root.after(120, self._rebuild)

    def _rebuild(self):
        self._resize_job = None
        if not self.winfo_exists():
            return
        try:
            self._build()
        except tk.TclError:
            pass

    def _build(self):
        self.delete("all")
        self._items = {}
        self._particles = []
        self._rings = []
        self._welcome_chars = []
        w = max(640, self.winfo_width())
        h = max(480, self.winfo_height())
        self.w, self.h = w, h
        self.cx = w / 2
        self.logo_y = int(h * 0.355)
        self.title_y = int(h * 0.468)
        self.sub_y = int(h * 0.512)
        self.btn_y = int(h * 0.585)
        self.btn_w, self.btn_h = 320, 56
        self._wel_y = int(h * 0.44)

        # backdrop: same scene, brighter than the working UI
        try:
            bg = gui.build_wallpaper(w, h)
        except Exception:
            bg = self.shell.wallpaper
        bg = ImageEnhance.Brightness(bg).enhance(1.52)
        bg = ImageEnhance.Contrast(bg).enhance(1.03)
        # vignette
        vig = Image.radial_gradient("L").resize((w, h), Image.Resampling.BILINEAR)
        vig = ImageOps.invert(vig).point(lambda v: int(v * 0.50))
        dark = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dark.putalpha(vig)
        bg = Image.alpha_composite(bg.convert("RGBA"), dark)
        # bake the text halos into the backdrop so Tk never has to alpha-blend
        # a translucent image over another image (that produces visible boxes).
        tg = _text_glow("破甲注入器", 72, (70, 236, 205, 58), 26)
        bg.paste(tg, (int(self.cx - tg.width / 2), int(self.title_y - tg.height / 2)), tg)
        wg = _text_glow("欢迎使用冰心破甲", 76, (80, 242, 212, 50), 30)
        bg.paste(wg, (int(self.cx - wg.width / 2), int(self._wel_y - wg.height / 2)), wg)
        bg = bg.convert("RGB")
        self._photos["bg"] = ImageTk.PhotoImage(bg)
        self.create_image(0, 0, anchor="nw", image=self._photos["bg"], tags="bg")

        # subtle bottom gradient for footer
        ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        for y in range(int(h * 0.80), h):
            t = (y - h * 0.80) / (h * 0.20)
            od.line((0, y, w, y), fill=(2, 5, 9, int(90 * t)))
        self._photos["ov"] = ImageTk.PhotoImage(ov)
        self.create_image(0, 0, anchor="nw", image=self._photos["ov"], tags="ov")

        # logo
        logo = _shield_base(106)
        self._photos["logo_in"] = _scaled_frames(logo, (0.72, 1.0), 12)
        self._photos["logo_out"] = list(reversed(self._photos["logo_in"]))
        self._items["logo"] = self.create_image(self.cx, self.logo_y, anchor="center",
                                                image=self._photos["logo_in"][-1], state="hidden")

        # title
        self._items["title"] = self.create_text(self.cx, self.title_y + 20, text="破甲注入器",
                                                fill=DARK, font=(gui.UI_FONT, 30, "bold"), anchor="center")
        self._items["sub"] = self.create_text(self.cx, self.sub_y + 10, text="B R E A K   / /   O P E N",
                                              fill=DARK, font=("Segoe UI", 9), anchor="center")

        # button
        self._photos["btn"] = {
            "normal": ImageTk.PhotoImage(_button_image(self.btn_w, self.btn_h, "normal")),
            "hover": ImageTk.PhotoImage(_button_image(self.btn_w, self.btn_h, "hover")),
            "press": ImageTk.PhotoImage(_button_image(self.btn_w, self.btn_h, "press")),
        }
        self._photos["btn_in"] = _scaled_frames(_button_image(self.btn_w, self.btn_h, "normal"), (0.88, 1.0), 12)
        self._items["btn"] = self.create_image(self.cx, self.btn_y, anchor="center",
                                               image=self._photos["btn_in"][-1], state="hidden")
        self._items["btn_text"] = self.create_text(self.cx, self.btn_y, text="破甲注入器",
                                                   fill="#04231E", font=(gui.UI_FONT, 13, "bold"),
                                                   anchor="center")

        # footer + skip
        self._items["footer"] = self.create_text(self.cx, h - 34, text="冷咖啡  ·  全自动破甲",
                                                 fill="#5D7183", font=(gui.UI_FONT, 8), anchor="center")
        self._items["skip"] = self.create_text(w - 26, h - 30, text="ESC 跳过", anchor="e",
                                               fill="#455767", font=(gui.UI_FONT, 8))

        # particles
        for i in range(55):
            halo = self.create_oval(0, 0, 0, 0, fill="#14332E", outline="", state="hidden")
            item = self.create_oval(0, 0, 0, 0, fill=MINT, outline="", state="hidden")
            self._particles.append({"id": item, "halo": halo, "x": 0, "y": 0, "vx": 0, "vy": 0,
                                    "life": 0, "age": 0, "size": 1, "hue": 0})

        # rings
        for i in range(3):
            self._rings.append(self.create_oval(0, 0, 0, 0, outline=MINT, width=2, state="hidden"))

        # welcome
        font = tkfont.Font(family=gui.UI_FONT, size=34, weight="bold")
        chars = "欢迎使用冰心破甲"
        widths = [font.measure(c) for c in chars]
        total = sum(widths)
        x = self.cx - total / 2
        for i, ch in enumerate(chars):
            cw = widths[i]
            fill = MINT if i in (4, 5) else WHITE
            item = self.create_text(x + cw / 2, self._wel_y + 26, text=ch, fill=DARK,
                                    font=(gui.UI_FONT, 34, "bold"), anchor="center")
            self._welcome_chars.append({"id": item, "x": x + cw / 2, "fill": fill, "i": i})
            x += cw
        self._items["wel_sub"] = self.create_text(self.cx, self._wel_y + 56,
                                                  text="I C E H E A R T   ·   B R E A K   E N G I N E",
                                                  fill=DARK, font=("Segoe UI", 9), anchor="center")
        self._items["wel_line"] = self.create_line(self.cx, self._wel_y + 82, self.cx, self._wel_y + 82,
                                                   fill="#14282C", width=1)

        self._apply_landing(0.0)
        self._hide_welcome()

    def _hide_welcome(self):
        for c in self._welcome_chars:
            self.itemconfigure(c["id"], state="hidden")
        for k in ("wel_sub", "wel_line"):
            self.itemconfigure(self._items[k], state="hidden")

    # ---------------------------------------------------------- animation
    def _tick(self):
        now = time.time()
        if self.phase == "landing":
            self._draw_landing(now - self.t0)
        else:
            self._draw_welcome(now - self.welcome_t0)
            if self.exiting:
                p = _seg(now - self.exit_t0, 0, self.exit_dur)
                self.place_configure(y=-int(self.h * _ease_in(p)))
                if p >= 1.0:
                    self._finish()
                    return
        self._job = self.after(16, self._tick)

    def _apply_landing(self, t):
        logo_p = _seg(t, 0.05, 0.50)
        title_p = _seg(t, 0.20, 0.50)
        sub_p = _seg(t, 0.36, 0.42)
        btn_p = _seg(t, 0.48, 0.50)
        if logo_p > 0:
            idx = max(0, min(11, int(round(_ease_out(logo_p) * 11))))
            self.itemconfigure(self._items["logo"], image=self._photos["logo_in"][idx], state="normal")
        else:
            self.itemconfigure(self._items["logo"], state="hidden")
        if title_p > 0:
            e = _ease_out(title_p)
            self.itemconfigure(self._items["title"], state="normal",
                               fill=gui._hex_mix(DARK, WHITE, e))
            self.coords(self._items["title"], self.cx, self.title_y + 20 * (1 - e))

        else:
            self.itemconfigure(self._items["title"], state="hidden")
        if sub_p > 0:
            e = _ease_out(sub_p)
            self.itemconfigure(self._items["sub"], state="normal", fill=gui._hex_mix(DARK, DIM, e))
            self.coords(self._items["sub"], self.cx, self.sub_y + 10 * (1 - e))
        else:
            self.itemconfigure(self._items["sub"], state="hidden")
        if btn_p > 0:
            idx = max(0, min(11, int(round(_ease_out(btn_p) * 11))))
            self.itemconfigure(self._items["btn"], image=self._photos["btn_in"][idx], state="normal")
            self.coords(self._items["btn"], self.cx, self.btn_y + 14 * (1 - _ease_out(btn_p)))
            self.coords(self._items["btn_text"], self.cx, self.btn_y + 14 * (1 - _ease_out(btn_p)))
            self.itemconfigure(self._items["btn_text"], state="normal",
                               fill=gui._hex_mix(DARK, "#04231E", _ease_out(btn_p)))
        else:
            self.itemconfigure(self._items["btn"], state="hidden")
            self.itemconfigure(self._items["btn_text"], state="hidden")

        if t > 1.0:
            drift = math.sin((t - 1.0) * 1.25) * 2.0
            if logo_p >= 1:
                self.coords(self._items["logo"], self.cx, self.logo_y + drift * 0.5)
            if title_p >= 1:
                self.coords(self._items["title"], self.cx, self.title_y + drift)
            if sub_p >= 1:
                self.coords(self._items["sub"], self.cx, self.sub_y + drift * 0.8)
            if btn_p >= 1 and not self._hover and not self._down:
                self.coords(self._items["btn"], self.cx, self.btn_y + drift * 0.4)
                self.coords(self._items["btn_text"], self.cx, self.btn_y + drift * 0.4)

    def _draw_landing(self, t):
        self._apply_landing(t)
        # gentle breathing glow on the button after the entrance
        if t > 1.0 and not self._down and not self._hover:
            k = 0.5 + 0.5 * math.sin((t - 1.0) * 2.2)
            # swap between two cached images is jarring; keep static, only pulse text
        self.itemconfigure(self._items["skip"], state="normal")

    def _start_welcome(self):
        self.phase = "welcome"
        self.welcome_t0 = time.time()
        self._hover = False
        self.configure(cursor="")
        self.itemconfigure(self._items["skip"], state="hidden")
        self._hide_welcome()
        # particles burst
        for p in self._particles:
            self._spawn_particle(p, burst=True)

    def _spawn_particle(self, p, burst=False):
        if burst:
            p["x"] = self.cx + random.uniform(-40, 40)
            p["y"] = self.btn_y + random.uniform(-12, 12)
            ang = random.uniform(0, math.tau)
            spd = random.uniform(70, 220)
            p["vx"] = math.cos(ang) * spd
            p["vy"] = math.sin(ang) * spd - random.uniform(30, 90)
            p["life"] = random.uniform(0.7, 1.3)
            p["size"] = random.choice((1, 2, 2))
        else:
            p["x"] = random.uniform(self.cx - 360, self.cx + 360)
            p["y"] = self._wel_y + random.uniform(-85, 38)
            p["vx"] = random.uniform(-12, 12)
            p["vy"] = random.uniform(-30, -10)
            p["life"] = random.uniform(1.4, 2.6)
            p["size"] = random.choice((1, 1, 2, 2, 3))
        p["age"] = 0.0001
        p["hue"] = random.choice((MINT, WHITE, "#9FE8FF", "#B7F6E8"))
        self.itemconfigure(p["id"], state="normal", fill=p["hue"])
        self.itemconfigure(p["halo"], state="normal", fill=gui._hex_mix("#0A1418", p["hue"], 0.55))

    def _draw_welcome(self, t):
        # fade the landing layer out
        out = _seg(t, 0.0, 0.28)
        if out < 1.0:
            idx = max(0, min(11, int(round((1 - _ease_out(out)) * 11))))
            self.itemconfigure(self._items["logo"], image=self._photos["logo_out"][idx], state="normal")
            self.itemconfigure(self._items["title"], fill=gui._hex_mix(WHITE, DARK, out))
            self.itemconfigure(self._items["sub"], fill=gui._hex_mix(DIM, DARK, out))
            self.itemconfigure(self._items["btn"], image=self._photos["btn_in"][idx], state="normal")
            self.itemconfigure(self._items["btn_text"], fill=gui._hex_mix("#04231E", DARK, out))
        else:
            for k in ("logo", "title", "sub", "btn", "btn_text"):
                self.itemconfigure(self._items[k], state="hidden")

        # rings
        for i, rid in enumerate(self._rings):
            p = _seg(t, 0.02 + i * 0.12, 1.10)
            if 0 < p < 1:
                r = 30 + 330 * _ease_out(p)
                col = gui._hex_mix("#8FF8DF", "#0A1418", p * 0.75)
                self.coords(rid, self.cx - r, self._wel_y - r, self.cx + r, self._wel_y + r)
                self.itemconfigure(rid, state="normal", outline=col, width=max(1, int(3 - 2 * p)))
            else:
                self.itemconfigure(rid, state="hidden")

        # particles
        dt = 0.016
        for p in self._particles:
            if p["age"] <= 0:
                continue
            p["age"] += dt
            if p["age"] >= p["life"]:
                if t < 2.05:
                    self._spawn_particle(p, burst=False)
                else:
                    self.itemconfigure(p["id"], state="hidden")
                    self.itemconfigure(p["halo"], state="hidden")
                    continue
            p["vy"] += 46 * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vx"] *= 0.995
            k = 1 - p["age"] / p["life"]
            col = gui._hex_mix("#0A1418", p["hue"], k)
            s = p["size"]
            self.coords(p["id"], p["x"] - s, p["y"] - s, p["x"] + s, p["y"] + s)
            self.itemconfigure(p["id"], fill=col)
            hs = s * 2.2
            self.coords(p["halo"], p["x"] - hs, p["y"] - hs, p["x"] + hs, p["y"] + hs)
            self.itemconfigure(p["halo"], fill=gui._hex_mix("#0A1418", p["hue"], 0.30 + 0.35 * k))

        # welcome text, staggered per character
        for c in self._welcome_chars:
            p = _seg(t, 0.30 + c["i"] * 0.055, 0.42)
            if p <= 0:
                self.itemconfigure(c["id"], state="hidden")
                continue
            e = _ease_out(p)
            eb = _ease_out_back(p)
            self.itemconfigure(c["id"], state="normal",
                               fill=gui._hex_mix(DARK, c["fill"], e))
            self.coords(c["id"], c["x"], self._wel_y + 26 * (1 - eb))
        sp = _seg(t, 1.02, 0.45)
        if sp > 0:
            self.itemconfigure(self._items["wel_sub"], state="normal",
                               fill=gui._hex_mix(DARK, "#7FA3B2", _ease_out(sp)))
        lp = _seg(t, 1.15, 0.55)
        if lp > 0:
            half = 128 * _ease_out(lp)
            self.coords(self._items["wel_line"], self.cx - half, self._wel_y + 82,
                        self.cx + half, self._wel_y + 82)
            self.itemconfigure(self._items["wel_line"], state="normal",
                               fill=gui._hex_mix("#0A1418", "#3D8F84", _ease_out(lp)))

        if not self.exiting and t > 2.55:
            self.exiting = True
            self.exit_t0 = time.time()
            self.exit_dur = 0.55

    # ---------------------------------------------------------- events
    def _inside_btn(self, x, y):
        return (abs(x - self.cx) <= self.btn_w / 2 + 10 and
                abs(y - self.btn_y) <= self.btn_h / 2 + 10)

    def _on_motion(self, e):
        if self._locked or self.phase != "landing" or not self._items.get("btn"):
            return
        inside = self._inside_btn(e.x, e.y)
        if inside != self._hover:
            self._hover = inside
            self.configure(cursor="hand2" if inside else "")
            if not self._down:
                img = self._photos["btn"]["hover" if inside else "normal"]
                self.itemconfigure(self._items["btn"], image=img)
                self.coords(self._items["btn"], self.cx, self.btn_y)
                self.coords(self._items["btn_text"], self.cx, self.btn_y)

    def _on_down(self, e):
        if self._locked or self.phase != "landing":
            return
        if self._inside_btn(e.x, e.y):
            self._down = True
            self.itemconfigure(self._items["btn"], image=self._photos["btn"]["press"])
            self.coords(self._items["btn_text"], self.cx, self.btn_y + 1)

    def _on_up(self, e):
        if self._locked or self.phase != "landing":
            return
        was = self._down
        self._down = False
        if was and self._inside_btn(e.x, e.y):
            self.itemconfigure(self._items["btn"], image=self._photos["btn"]["hover"])
            self._start_welcome()
        elif was:
            self.itemconfigure(self._items["btn"], image=self._photos["btn"]["normal"])
            self.coords(self._items["btn_text"], self.cx, self.btn_y)

    def _on_esc(self, e):
        if self._locked or self.exiting:
            return
        self.exiting = True
        self.exit_t0 = time.time()
        self.exit_dur = 0.30

    def _finish(self):
        if getattr(self, "_dark_job", None):
            try:
                self.root.after_cancel(self._dark_job)
            except Exception:
                pass
            self._dark_job = None
        if self._resize_job:
            try:
                self.after_cancel(self._resize_job)
            except Exception:
                pass
            self._resize_job = None
        if self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None
        try:
            if self._esc_id:
                self.root.unbind("<Escape>", self._esc_id)
        except Exception:
            pass
        try:
            gui.enable_dark_title(self.root)
        except Exception:
            pass
        self.destroy()
        if self.on_finish:
            self.on_finish()


def launch(root, shell, on_finish=None):
    return IntroOverlay(root, shell, on_finish)