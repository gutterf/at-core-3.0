import io
p = r"C:\Users\admin\Desktop\冷咖啡全自动破甲\assets\_compose.py"
s = io.open(p, encoding="utf-8").read()
s = s.replace('''base = Image.alpha_composite(base.convert("RGBA"), shadow, dest=(ex - 60 + 4, ey - 60 + 8)).convert("RGB")
base = Image.alpha_composite(base.convert("RGBA"), glow, dest=(ex - 45, ey - 45)).convert("RGB")''',
'''base_rgba = base.convert("RGBA")
base_rgba.paste(shadow, (ex - 60 + 4, ey - 60 + 8), shadow)
base_rgba.paste(glow, (ex - 45, ey - 45), glow)
base = base_rgba.convert("RGB")''')
io.open(p, "w", encoding="utf-8", newline="\n").write(s)