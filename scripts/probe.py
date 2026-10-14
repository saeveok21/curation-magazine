import re, json, requests
from urllib.parse import quote
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36","Accept-Language":"ko-KR,ko;q=0.9"}
out=[]
def log(*a): out.append(" ".join(str(x) for x in a))
js=requests.get("https://t1.kakaocdn.net/brunch/static/prod/20261014133315/production/B.Keyword.min.js",headers=UA,timeout=20).text
for m in re.finditer(r"/v1/top/keyword/", js):
    log("CTX", js[max(0,m.start()-500):m.start()+500].replace("\n"," "))
kw="IT_트렌드"; page="https://brunch.co.kr/keyword/"+quote(kw)+"?q=g"
H={**UA,"Referer":page,"Accept":"application/json, text/javascript, */*","Origin":"https://brunch.co.kr"}
for u in ["https://api.brunch.co.kr/v1/top/keyword/group/"+quote(kw),
          "https://api.brunch.co.kr/v1/top/keyword/group/"+quote(kw)+"?publishTime=&pickContentId=",
          "https://api.brunch.co.kr/v1/top/keyword/"+quote(kw),
          "https://api.brunch.co.kr/v1/top/keyword/manual/"+quote(kw)]:
    try:
        r=requests.get(u,headers=H,timeout=20); log("CAND",u,r.status_code,r.text[:1500].replace("\n"," "))
    except Exception as e: log("ERR",u,e)
import os; os.makedirs("data/debug",exist_ok=True)
open("data/debug/probe.txt","w").write("\n".join(out))
