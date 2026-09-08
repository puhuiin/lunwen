import sys, json
src, dst = sys.argv[1], sys.argv[2]
t = open(src, encoding='utf-8').read()
idx = t.find('[{"type":"text"')
body = t[idx:] if idx >= 0 else t
obj = json.loads(body)
inner = obj[0]['text']
open(dst, 'w', encoding='utf-8').write(inner)
print('wrote', dst, len(inner), 'chars')
