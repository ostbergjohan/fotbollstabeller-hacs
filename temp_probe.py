import re, urllib.request

url='https://www.fotbollstabeller.nu/home/group/allsvenskan-herrar'
req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
html=urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'replace')
print('len', len(html))
pat = r'/_next/static/chunks/[^"\']+\.js'
srcs = sorted(set(re.findall(pat, html)))
print('scripts', len(srcs))
for s in srcs[:10]:
    full='https://www.fotbollstabeller.nu' + s
    req=urllib.request.Request(full, headers={'User-Agent':'Mozilla/5.0'})
    js=urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'replace')
    hits=[]
    for kw in ['/api','fetch(','allsvenskan','tabell','group','standings','poang','resultat']:
        if kw.lower() in js.lower():
            hits.append(kw)
    if hits:
        print('CHUNK', s, hits[:10])

pos = html.lower().find('allsvenskan')
print('pos', pos)
for i in range(3):
    start = max(0, pos - 500 + i*1200)
    end = min(len(html), start + 1200)
    snippet = html[start:end]
    print('--- snippet', i, '---')
    print(snippet)
    print('--- end snippet ---')
