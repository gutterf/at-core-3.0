import io, re
p = r'C:\Users\admin\Desktop\冷咖啡全自动破甲\coffee_breaker.py'
lines = io.open(p, encoding='utf-8').read().split('\n')
def owner(n):
    for i in range(n-1, -1, -1):
        m = re.match(r'\s*def (\w+)', lines[i])
        if m: return m.group(1)
    return '?'
tgt = [1529,1710,1714,1738,3108]
print('A', ' '.join(f'{t}:{owner(t)}' for t in tgt))
wr = [i for i,l in enumerate(lines,1) if ('__NAME__' in l or '.md' in l) and i>1000]
print('B', wr[:12])
