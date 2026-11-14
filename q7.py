import io, re
p = r'C:\Users\admin\Desktop\冷咖啡全自动破甲\coffee_breaker.py'
L = io.open(p, encoding='utf-8').read().split('\n')
def owner(n):
    for i in range(n-1, -1, -1):
        m = re.match(r'\s*def (\w+)', L[i])
        if m: return m.group(1)
pat = re.compile(r'(open\(.*[\'"]w|write_text|\.write\(|OUT_DIR|save_)')
h = [(i,owner(i)) for i,l in enumerate(L,1) if pat.search(l) and i>1500]
print(' '.join(f'{i}:{o}' for i,o in h[:14]))
