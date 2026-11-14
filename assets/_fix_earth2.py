import io
p = r"C:\Users\admin\Desktop\冷咖啡全自动破甲\assets\_compose.py"
s = io.open(p, encoding="utf-8").read()
s = s.replace("diam = 372", "diam = 352")
old = '''ec = Image.composite(ec, dark, shade)
ec = ImageEnhance.Brightness(ec).enhance(0.92)
'''
new = '''ec = Image.composite(ec, dark, shade)
ec = ImageEnhance.Brightness(ec).enhance(0.92)
ec = ec.filter(ImageFilter.GaussianBlur(0.5))
rim = Image.new("L", (diam, diam), 0)
ImageDraw.Draw(rim).ellipse((1, 1, diam - 2, diam - 2), outline=255, width=9)
rim = rim.filter(ImageFilter.GaussianBlur(6))
ec = Image.composite(ec, Image.blend(ec, Image.new("RGB", ec.size, (14, 20, 30)), 0.50), rim)
'''
assert old in s
s = s.replace(old, new, 1)

old2 = '''base_rgba = base.convert("RGBA")
base_rgba.paste(shadow, (ex - 60 + 4, ey - 60 + 8), shadow)
base_rgba.paste(glow, (ex - 45, ey - 45), glow)
base = base_rgba.convert("RGB")'''
new2 = '''base_rgba = base.convert("RGBA")
halo = Image.new("RGBA", (diam + 220, diam + 220), (0, 0, 0, 0))
hd = ImageDraw.Draw(halo)
for rr, aa in ((diam // 2 + 6, 52), (diam // 2 + 18, 26)):
    hd.ellipse((110 - rr, 110 - rr, 110 + rr, 110 + rr), outline=(110, 178, 238, aa), width=12)
halo = halo.filter(ImageFilter.GaussianBlur(26))
base_rgba.paste(halo, (ex - 110, ey - 110), halo)
base_rgba.paste(shadow, (ex - 60 + 4, ey - 60 + 8), shadow)
base_rgba.paste(glow, (ex - 45, ey - 45), glow)
base = base_rgba.convert("RGB")'''
assert old2 in s
s = s.replace(old2, new2, 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched")