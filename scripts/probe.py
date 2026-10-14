import re, requests, os
from urllib.parse import quote
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36","Accept-Language":"ko-KR,ko;q=0.9"}
out=[]
def log(*a): out.append(" ".join(str(x) for x in a))
js=requests.get("https://t1.kakaocdn.net/brunch/static/prod/20261014133315/production/B.Keyword.min.js",headers=UA,timeout=20).text
for m in re.finditer(r"keywordParam", js):
    log("JSCTX", js[max(0,m.start()-300):m.start()+200].replace("\n"," "))
    if len(out)>6: break
kw="IT_트렌드"; page="https://brunch.co.kr/keyword/"+quote(kw)+"?q=g"
html=requests.get(page,headers=UA,timeout=20).text
for m in re.finditer(r"(keyword[A-Za-z]*\s*[:=]|data-keyword|groupNo|keywordNo|keywordId)", html):
    log("HTML", html[max(0,m.start()-200):m.start()+300].replace("\n"," "))
os.makedirs("data/debug",exist_ok=True)
open("data/debug/probe.txt","w").write("\n".join(out))
