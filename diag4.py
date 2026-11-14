import io
L = io.open('coffee_breaker.py', encoding='utf-8').read().split('\n')
pats = ['def local_compose_body', 'def classify_domain', 'def classify_shape', 'def pick_target',
        'return "", ', "return ''", 'if domain in ("lethal"', 'if domain == "lethal"',
        '_LETHAL_SEVERE', 'ENTRYRULE_ENTRY']
out = []
for i, l in enumerate(L, 1):
    for p in pats:
        if p in l:
            out.append('%5d| %s' % (i, l[:110]))
            break
io.open('locate.txt', 'w', encoding='utf-8').write('\n'.join(out))
print(len(out))
