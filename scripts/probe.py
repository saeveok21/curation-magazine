import sys, os, re
sys.path.insert(0, "scripts")
import collect
out = []
for vid in ["UfT0I0LUPr0", "IlULKVU7GUY"]:
    try:
        r = collect.session.get(f"https://www.youtube.com/watch?v={vid}", timeout=20)
        w = r.text
        out.append(f"{vid} status={r.status_code} len={len(w)} videoDetails={'videoDetails' in w} shortDesc={'shortDescription' in w} botcheck={'not a bot' in w} title={re.findall(r'<title>([^<]*)', w)[:1]}")
        i = w.find('"videoDetails"'); out.append(w[i:i+300] if i >= 0 else "no videoDetails")
        out.append("dates " + str(re.findall(r'"(?:publishDate|uploadDate|datePublished)"[^,]{0,60}', w)[:4]))
        out.append("meta " + str(re.findall(r'<meta[^>]+(?:itemprop="(?:datePublished|uploadDate)"|name="title"|property="og:description")[^>]*>', w)[:4]))
    except Exception as e:
        out.append(f"{vid} ERR {e}")
os.makedirs("data/debug", exist_ok=True)
open("data/debug/probe.txt", "w").write("\n".join(out))
