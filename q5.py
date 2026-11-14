import io
p = r'C:\Users\admin\Desktop\冷咖啡全自动破甲\coffee_breaker.py'
lines = io.open(p, encoding='utf-8').read().split('\n')
hits = [i for i,l in enumerate(lines,1) if '角色层' in l or '规格层' in l]
print('ROLE', hits)
w = [i for i,l in enumerate(lines,1) if 'output' in l and ('open(' in l or 'write' in l)]
print('WR', w)
