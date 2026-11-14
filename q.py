import re
F = 'coffee_breaker.py'
SRC = open(F, encoding='utf-8').read()
L = SRC.split('\n')

def show(a, b, w=200):
    for i in range(a - 1, b):
        print(i + 1, L[i][:w])

def find(s, a=1, b=0, w=90):
    b = b or len(L)
    return [(i + 1, L[i].strip()[:w]) for i in range(a - 1, min(b, len(L))) if s in L[i]]

def defs():
    return [i + 1 for i, l in enumerate(L) if re.match(r'^    def ', l)]

def num(s):
    return len(re.findall(s, SRC))
