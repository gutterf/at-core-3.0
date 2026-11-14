import io
p = r"C:\Users\admin\Desktop\冷咖啡全自动破甲\assets\_compose.py"
s = io.open(p, encoding="utf-8").read()
old = '''ec = ec.resize((diam, diam), Image.Resampling.LANCZOS)
ec = ImageEnhance.Brightness(ec).enhance(0.90)
ec = ImageEnhance.Color(ec).enhance(1.06)
ec = Image.blend(ec, Image.new("RGB", ec.size, (60, 110, 160)), 0.10)
'''
new = '''ec = ec.resize((diam, diam), Image.Resampling.LANCZOS)
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
'''
assert old in s
s = s.replace(old, new, 1)
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("patched")