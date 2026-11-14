import os, glob, io
BASE = r'C:\Users\admin\Desktop\冷咖啡全自动破甲'
mds = []
for root, dirs, files in os.walk(BASE):
    if '.git' in root: continue
    for f in files:
        if f.endswith('.md'):
            p = os.path.join(root, f)
            mds.append((os.path.getsize(p), os.path.relpath(p, BASE)))
mds.sort(reverse=True)
lines = [f'{s} {r}' for s, r in mds[:40]]
io.open('q10.txt','w',encoding='utf-8').write('\n'.join(lines))
print(len(mds), mds[0][1][:40] if mds else '-')
