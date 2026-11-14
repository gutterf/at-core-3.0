import json, io
d = json.load(io.open('_diag_out.json', encoding='utf-8'))
bad = [i for i, x in enumerate(d) if not x.get('body_ok')]
miss = [i for i, x in enumerate(d) if not (x.get('domain') and x.get('shape') and x.get('target'))]
print('N=%d PASS=%d body_fail=%s field_miss=%s' % (len(d), len(d) - len(bad), bad or '-', miss or '-'))
