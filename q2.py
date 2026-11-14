import sys
sys.path.insert(0, r'C:\Users\admin\Desktop\冷咖啡全自动破甲')
import coffee_breaker as C
ns = [n for n in dir(C) if not n.startswith('__')]
print(len(ns))
print(' '.join(ns)[:200])
