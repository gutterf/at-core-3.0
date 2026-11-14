import io
src = io.open(r'C:\Users\admin\Desktop\冷咖啡全自动破甲\coffee_breaker.py', encoding='utf-8').read()
lines = src.split('\n')
for i, l in enumerate(lines, 1):
    if '环节序号' in l or '关键条件' in l or '产物 =' in l:
        print(i, l.strip()[:70])
