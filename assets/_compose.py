# -*- coding: utf-8 -*-
import math, os, random
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

ASSETS = r"C:\Users\admin\Desktop\冷咖啡全自动破甲\assets"
W, H = 2400, 1518

sea = Image.open(os.path.join(ASSETS, "sea_base.jpg")).convert("RGB")
scale = max(W / sea.width, H / sea.height)
sea = sea.resize((int(sea.width * scale) + 1, int(sea.height * scale) + 1), Image.Resampling.LANCZOS)
left = (sea.width - W) // 2
top = (sea.height - H) // 2
base = sea.crop((left, top, left + W, top + H))

base = ImageEnhance.Color(base).enhance(0.62)
base = ImageEnhance.Brightness(base).enhance(0.60)
base = ImageEnhance.Contrast(base).enhance(1.07)
tint = Image.new("RGB", (W, H), (8, 22, 42))
base = Image.blend(base, tint, 0.24)

# horizon around 54%
horizon = int(H * 0.545)

# ---- Earth ----
earth = Image.open(os.path.join(ASSETS, "earth_apollo17.jpg")).convert("RGB")
m = earth.convert("L").point(lambda v: 255 if v > 18 else 0)
box = m.getbbox()
x0, y0, x1, y1 = box
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
r = min(x1 - x0, y1 - y0) / 2
pad = 6
ec = earth.crop((int(cx - r - pad), int(cy - r - pad), int(cx + r + pad), int(cy + r + pad)))
diam = 352
ec = ec.resize((diam, diam), Image.Resampling.LANCZOS)
ec = ImageEnhance.Brightness(ec).enhance(0.88)
ec = ImageEnhance.Color(ec).enhance(0.94)
ec = Image.blend(ec, Image.new("RGB", ec.size, (40, 52, 68)), 0.07)

# phase shading: lit from upper-right, terminator toward lower-left
small = Image.new("L", (64, 64))
for yy in range(64):
    for xx in range(64):
        t = (xx / 63.0) * 0.62 + (1 - yy / 63.0) * 0.38
        small.putpixel((xx, yy), int(58 + 197 * t))
shade = small.resize((diam, diam), Image.Resampling.BILINEAR)
dark = ImageEnhance.Brightness(ec).enhance(0.34)
ec = Image.composite(ec, dark, shade)
ec = ImageEnhance.Brightness(ec).enhance(0.92)
ec = ec.filter(ImageFilter.GaussianBlur(0.5))
rim = Image.new("L", (diam, diam), 0)
ImageDraw.Draw(rim).ellipse((1, 1, diam - 2, diam - 2), outline=255, width=9)
rim = rim.filter(ImageFilter.GaussianBlur(6))
ec = Image.composite(ec, Image.blend(ec, Image.new("RGB", ec.size, (14, 20, 30)), 0.50), rim)

mask = Image.new("L", (diam * 2, diam * 2), 0)
ImageDraw.Draw(mask).ellipse((4, 4, diam * 2 - 4, diam * 2 - 4), fill=255)
mask = mask.resize((diam, diam), Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(0.8))
ec.putalpha(mask)

# atmosphere glow
glow = Image.new("RGBA", (diam + 90, diam + 90), (0, 0, 0, 0))
gd = ImageDraw.Draw(glow)
for i, a in ((0, 70), (6, 42), (16, 20)):
    gd.ellipse((45 - i, 45 - i, diam + 45 + i, diam + 45 + i),
               outline=(120, 190, 245, a), width=3)
glow = glow.filter(ImageFilter.GaussianBlur(10))

earth_cx, earth_cy = int(W * 0.855), int(H * 0.255)
ex = earth_cx - diam // 2
ey = earth_cy - diam // 2

# soft shadow behind
shadow = Image.new("RGBA", (diam + 120, diam + 120), (0, 0, 0, 0))
ImageDraw.Draw(shadow).ellipse((60, 66, diam + 60, diam + 66), fill=(0, 0, 0, 120))
shadow = shadow.filter(ImageFilter.GaussianBlur(26))
base_rgba = base.convert("RGBA")
halo = Image.new("RGBA", (diam + 220, diam + 220), (0, 0, 0, 0))
hd = ImageDraw.Draw(halo)
for rr, aa in ((diam // 2 + 6, 52), (diam // 2 + 18, 26)):
    hd.ellipse((110 - rr, 110 - rr, 110 + rr, 110 + rr), outline=(110, 178, 238, aa), width=12)
halo = halo.filter(ImageFilter.GaussianBlur(26))
base_rgba.paste(halo, (ex - 110, ey - 110), halo)
base_rgba.paste(shadow, (ex - 60 + 4, ey - 60 + 8), shadow)
base_rgba.paste(glow, (ex - 45, ey - 45), glow)
base = base_rgba.convert("RGB")
base.paste(ec, (ex, ey), ec)

# ---- light reflection on water, under the earth ----
ref = Image.new("RGBA", (W, H), (0, 0, 0, 0))
rd = ImageDraw.Draw(ref)
for i in range(0, H - horizon):
    a = int(24 * math.exp(-i / 210.0))
    if a <= 0:
        continue
    half = int(46 + i * 0.30)
    rd.rectangle((earth_cx - half, horizon + i, earth_cx + half, horizon + i + 1),
                 fill=(130, 190, 230, a))
ref = ref.filter(ImageFilter.GaussianBlur(16))
base = Image.alpha_composite(base.convert("RGBA"), ref).convert("RGB")

# ---- haze band at horizon ----
haze = Image.new("RGBA", (W, H), (0, 0, 0, 0))
ImageDraw.Draw(haze).rectangle((0, horizon - 46, W, horizon + 40), fill=(150, 185, 205, 34))
haze = haze.filter(ImageFilter.GaussianBlur(34))
base = Image.alpha_composite(base.convert("RGBA"), haze).convert("RGB")

# ---- stars in dark sky ----
random.seed(20261031)
stars = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(stars)
for _ in range(420):
    sx = random.randint(0, W - 1)
    sy = random.randint(0, int(H * 0.50))
    v = random.randint(55, 150)
    s = 1 if random.random() < 0.85 else 2
    sd.ellipse((sx, sy, sx + s, sy + s), fill=(210, 228, 255, v))
stars = stars.filter(ImageFilter.GaussianBlur(0.4))
lummask = base.convert("L").point(lambda v: 255 if v < 72 else 0)
stars.putalpha(ImageChops.multiply(stars.getchannel("A"), lummask))
base = Image.alpha_composite(base.convert("RGBA"), stars).convert("RGB")

# ---- cinematic vignette ----
vig = Image.radial_gradient("L").resize((W, H), Image.Resampling.BILINEAR)
vig = ImageOps.invert(vig).point(lambda v: int(v * 0.42))
dark = Image.new("RGBA", (W, H), (0, 0, 0, 0))
dark.putalpha(vig)
base = Image.alpha_composite(base.convert("RGBA"), dark).convert("RGB")

# ---- UI legibility gradients + final grade ----
ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
od = ImageDraw.Draw(ov)
for y in range(int(H * 0.30)):
    a = int(92 * (1 - y / (H * 0.30)) ** 1.4)
    od.line((0, y, W, y), fill=(2, 5, 9, a))
for y in range(int(H * 0.72), H):
    t = (y - H * 0.72) / (H * 0.28)
    od.line((0, y, W, y), fill=(2, 5, 9, int(96 * t)))
base = Image.alpha_composite(base.convert("RGBA"), ov).convert("RGB")
base = ImageEnhance.Brightness(base).enhance(0.94)

# grain
noise = Image.effect_noise((W, H), 6).convert("L")
n = Image.new("RGBA", (W, H), (255, 255, 255, 0))
n.putalpha(noise.point(lambda v: 5 if v > 128 else 0))
base = Image.alpha_composite(base.convert("RGBA"), n).convert("RGB")

out = os.path.join(ASSETS, "bg_ocean_earth.jpg")
base.save(out, quality=93, subsampling=1)
print("saved", out, base.size, os.path.getsize(out))