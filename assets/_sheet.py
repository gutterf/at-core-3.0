from PIL import Image, ImageDraw
import os
base = r"C:\Users\admin\Desktop\冷咖啡全自动破甲\assets\cand"
files = [os.path.join(base, "%02d.jpg" % i) for i in range(8)]
thumbs = []
for f in files:
    im = Image.open(f).convert("RGB")
    im.thumbnail((420, 260))
    canvas = Image.new("RGB", (420, 260), (18,18,20))
    canvas.paste(im, ((420-im.width)//2, (260-im.height)//2))
    d = ImageDraw.Draw(canvas); d.text((8,8), os.path.basename(f), fill=(255,255,255))
    thumbs.append(canvas)
sheet = Image.new("RGB", (420*4, 260*2), (10,10,12))
for i,t in enumerate(thumbs):
    sheet.paste(t, ((i%4)*420, (i//4)*260))
sheet.save(r"C:\Users\admin\Documents\ChatGPT\1\evidence\ui\candidates.jpg", quality=88)
print("ok", sheet.size)