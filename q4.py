import sys, io, inspect
sys.path.insert(0, r'C:\Users\admin\Desktop\冷咖啡全自动破甲')
import coffee_breaker as C
print('NAMES', ' '.join(n for n in dir(C) if n.isupper())[:240])
