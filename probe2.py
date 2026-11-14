import urllib.request

for url in ['https://www.fotbollstabeller.nu/allsvenskan', 'https://www.fotbollstabeller.nu/home/group/allsvenskan-herrar']:
    req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
    html=urllib.request.urlopen(req, timeout=20).read().decode('utf-8','replace')
    print('URL', url)
    for kw in ['Hammarby','Malmö','AIK','tabell','poäng','lag','position','rank','Sirius','MFF']:
        idx=html.lower().find(kw.lower())
        print('KW', kw, 'idx', idx)
        if idx!=-1:
            print(html[max(0,idx-200):idx+700])
            print('---')
    print('====')
