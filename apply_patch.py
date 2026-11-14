# -*- coding: utf-8 -*-
import io, shutil, re, sys

SRC = 'coffee_breaker.py'
FRAG = '_patch_frag.py'
shutil.copy(SRC, SRC + '.bak_v2')

src = io.open(SRC, encoding='utf-8').read()
frag = io.open(FRAG, encoding='utf-8').read()

if '_orig_compose_body' in src:
    print('ALREADY_PATCHED')
    sys.exit(0)

L = src.split('\n')
idx = None
for i, l in enumerate(L):
    if l.startswith('if __name__'):
        idx = i
        break
if idx is None:
    idx = len(L)

head = '\n'.join(L[:idx])
tail = '\n'.join(L[idx:])
out = head + '\n\n' + frag + '\n\n' + tail

io.open(SRC, 'w', encoding='utf-8').write(out)
print('PATCHED_AT_LINE', idx + 1, 'NEW_LINES', len(out.split('\n')))
