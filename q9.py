import io
p = r'C:\Users\admin\Desktop\冷咖啡全自动破甲\coffee_breaker.py'
L = io.open(p, encoding='utf-8').read().split('\n')
out = []
for n in (124, 5062, 6152):
    out.append(f'--- {n} ---')
    out.append('\n'.join(x.strip()[:100] for x in L[n-3:n+4]))
open('q9.txt','w',encoding='utf-8').write('\n'.join(out))
print('ok')
