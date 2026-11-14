import io, re
p = r'C:\Users\admin\Desktop\冷咖啡全自动破甲\coffee_breaker.py'
L = io.open(p, encoding='utf-8').read().split('\n')
h = [i for i,l in enumerate(L,1) if 'strftime' in l]
print('TS', h)
for i in h:
    print(i, L[i-1].strip()[:90])
