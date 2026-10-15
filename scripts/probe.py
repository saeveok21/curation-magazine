import sys, os, re, json
sys.path.insert(0, "scripts")
import collect
out = []
pid = "PLXvTERtQ_HV-Nm5gT6dVjKITGeyE4Vs5G"
try:
    r = collect.session.get(f"https://www.youtube.com/feeds/videos.xml?playlist_id={pid}", timeout=20)
    out.append(f"RSS {r.status_code} {len(r.text)} {r.text[:200]!r}")
except Exception as e:
    out.append(f"RSS ERR {e}")
html = collect.get(f"https://www.youtube.com/playlist?list={pid}").text
out.append(f"PAGE len={len(html)} ytInitialData={'ytInitialData' in html} consent={'consent' in html[:5000].lower()}")
data = collect._yt_json(html, "ytInitialData")
keys = set()
def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            if k.endswith("Renderer") or k.endswith("ViewModel"): keys.add(k)
            walk(v)
    elif isinstance(o, list):
        for v in o: walk(v)
walk(data)
out.append("renderers: " + ", ".join(sorted(keys)))
out.append("videoIds: " + ", ".join(list(dict.fromkeys(re.findall(r'"videoId":"([\w-]{11})"', html)))[:15]))
r = list(collect._walk(data, "playlistVideoRenderer"))
out.append(f"pvr count {len(r)}")
if r:
    vid = r[0]["videoId"]
    w = collect.get(f"https://www.youtube.com/watch?v={vid}").text
    out.append(f"WATCH {vid} len={len(w)} shortDesc={'shortDescription' in w} publishDate={re.findall(r'\"(?:publishDate|uploadDate)\":\"([^\"]+)\"', w)[:2]}")
os.makedirs("data/debug", exist_ok=True)
open("data/debug/probe.txt", "w").write("\n".join(out))
