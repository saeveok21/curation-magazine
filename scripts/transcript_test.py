import sys
from youtube_transcript_api import YouTubeTranscriptApi
ids = sys.argv[1:]
api = YouTubeTranscriptApi()
for vid in ids:
    try:
        tl = api.list(vid)
        langs = [(t.language_code, t.is_generated) for t in tl]
        t = tl.find_transcript(['ko', 'en'])
        data = t.fetch()
        text = " ".join(s.text for s in data)
        print(f"[ok] {vid} langs={langs} chars={len(text)} :: {text[:200]}")
    except Exception as e:
        print(f"[fail] {vid} {type(e).__name__}: {str(e)[:300]}")
