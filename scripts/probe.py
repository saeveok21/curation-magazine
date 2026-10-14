import re, json, requests
from urllib.parse import urljoin, quote
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36","Accept-Language":"ko-KR,ko;q=0.9"}
out=[]
def log(*a): out.append(" ".join(str(x) for x in a))
def g(u, **kw):
    try:
        r=requests.get(u,headers={**UA,**kw.get("h",{})},timeout=20); r.encoding=r.apparent_encoding if not r.encoding else r.encoding
        return r
    except Exception as e:
        log("ERR",u,e); return None
# thescoop
r=g("https://www.thescoop.co.kr/rssIndex.html")
if r: log("SCOOP rssIndex",r.status_code, sorted(set(re.findall(r'[\w:/.\-]*rss[\w/.\-]*\.xml',r.text)))[:20])
for u in ["https://www.thescoop.co.kr/rss/allArticle.xml","https://www.thescoop.co.kr/rss/S1N1.xml"]:
    r=g(u)
    if r: log("SCOOP",u,r.status_code,len(r.text),r.text[:600].replace("\n"," "))
# brunch
kw="IT_트렌드"
page=f"https://brunch.co.kr/keyword/{quote(kw)}?q=g"
r=g(page)
if r:
    log("BRUNCH page",r.status_code,len(r.text))
    scripts=re.findall(r'<script[^>]+src="([^"]+)"',r.text)
    log("scripts",scripts)
    log("inline api refs",sorted(set(re.findall(r'api\.brunch\.co\.kr[^"\'\s<]*',r.text)))[:40])
    for s in scripts:
        su=urljoin(page,s)
        sr=g(su)
        if not sr: continue
        refs=sorted(set(re.findall(r'["\'`](/v\d+/[A-Za-z0-9_/{}$.:\-]*)',sr.text)))
        kref=[x for x in refs if "keyword" in x.lower() or "article" in x.lower()]
        if kref: log("JS",su,len(sr.text),kref[:80])
        hosts=sorted(set(re.findall(r'https?://[a-z0-9.\-]*brunch[a-z0-9.\-]*',sr.text)))
        if hosts: log("hosts",su,hosts)
cands=[f"https://api.brunch.co.kr/v1/keyword/{quote(kw)}/article",
       f"https://api.brunch.co.kr/v2/keyword/{quote(kw)}/article",
       f"https://api.brunch.co.kr/v1/top/keyword/group/{quote(kw)}",
       f"https://api.brunch.co.kr/v2/top/keyword/group/{quote(kw)}",
       f"https://api.brunch.co.kr/v1/search/article?q={quote('IT 트렌드')}&page=1&pageSize=5&highlighter=n&escape=y&sortBy=recency",
       f"https://api.brunch.co.kr/v1/keyword/group/{quote(kw)}"]
for u in cands:
    r=g(u,h={"Referer":page,"Accept":"application/json"})
    if r: log("CAND",u,r.status_code,r.text[:500].replace("\n"," "))
import os; os.makedirs("data/debug",exist_ok=True)
open("data/debug/probe.txt","w").write("\n".join(out))
