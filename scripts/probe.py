import re, requests, os, json
from urllib.parse import quote
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36","Accept-Language":"ko-KR,ko;q=0.9"}
out=[]
def log(*a): out.append(" ".join(str(x) for x in a))
dec=json.JSONDecoder()
for kw in ["IT_트렌드","알수록_좋은_경제","지구한바퀴_세계여행","오늘은_이런_책"]:
    page="https://brunch.co.kr/keyword/"+quote(kw)+"?q=g"
    html=requests.get(page,headers=UA,timeout=20).text
    m=re.search(r'id="keywordParam"[^>]*value="([^"]*)"',html) or re.search(r'value="([^"]*)"[^>]*id="keywordParam"',html)
    log("KW",kw,"param=",m.group(1) if m else None, "type=", (re.search(r'id="keywordType"[^>]*value="([^"]*)"',html) or [None,None])[1])
    i=html.find('[{"article":')
    log("arraystart",i, html[max(0,i-150):i].replace("\n"," "))
    if i<0: continue
    arr,_=dec.raw_decode(html[i:])
    log("count",len(arr))
    a=arr[0]["article"]
    log("keys",sorted(a.keys()))
    for e in arr[:3]:
        a=e["article"]
        log("ART",a.get("no"),a.get("userId"),a.get("userName"),a.get("title"),a.get("subTitle"),a.get("publishTimestamp") or a.get("publishTime"),e.get("timestamp"),str(a.get("contentSummary") or a.get("summary") or "")[:200])
os.makedirs("data/debug",exist_ok=True)
open("data/debug/probe.txt","w").write("\n".join(out))
