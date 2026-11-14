import io,re,sys
k=sys.argv[1]
d=int(sys.argv[2]) if len(sys.argv)>2 else 0
L=io.open('coffee_breaker.py',encoding='utf-8',errors='replace').read().split('\n')
out=[]
for i,s in enumerate(L):
    m=re.match(r'\s*def\s+(\w+)',s)
    if m and k in m.group(1):
        ind='>' if s.startswith('def ') else '.'
        out.append(f'{ind}{i+1}:{m.group(1)}')
print(len(out));print(' '.join(out[d:d+14]))
