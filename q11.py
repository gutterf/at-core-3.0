import json, sys, io
d = json.load(io.open('_diag_out.json', encoding='utf-8'))
a, b = int(sys.argv[1]), int(sys.argv[2])
for i in range(a, min(b, len(d))):
    x = d[i]
    print(i, x.get('domain'), x.get('shape'), x.get('target'), 'body_ok=%s' % x.get('body_ok'))
