"""큐레이션 매거진 수집기.

sources.json 에 적힌 소스(유튜브 채널·재생목록, DBR, 100주년기념교회 게시판)에서
새 콘텐츠 목록을 모아 data/items.json 에 누적 저장한다.
요약은 여기서 하지 않는다. (Claude 예약 작업이 이 파일을 읽어 요약한다.)
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources.json"
ITEMS = ROOT / "data" / "items.json"
STATUS = ROOT / "data" / "status.json"

MAX_ITEMS = 500           # 파일에 보관할 최대 개수
FIRST_RUN_PER_SOURCE = 5  # 소스를 처음 수집할 때 가져올 개수
PER_RUN_PER_SOURCE = 15   # 이후 실행마다 소스당 확인할 최대 개수
TEXT_LIMIT = 4000         # 본문/설명 저장 길이

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)
session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"})

NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get(url: str) -> requests.Response:
    r = session.get(url, timeout=25)
    r.raise_for_status()
    if not r.encoding or r.encoding.lower() in ("iso-8859-1", "ascii"):
        r.encoding = r.apparent_encoding
    return r


def clean(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def make_id(source_id: str, key: str) -> str:
    return f"{source_id}-{hashlib.sha1(key.encode()).hexdigest()[:12]}"


# ---------------- 유튜브 ----------------

def collect_youtube(src: dict, limit: int) -> list[dict]:
    if src["type"] == "youtube_channel":
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={src['channel_id']}"
    else:
        url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={src['playlist_id']}"
    root = ET.fromstring(get(url).content)
    out = []
    for entry in root.findall("atom:entry", NS)[:limit]:
        vid = entry.findtext("yt:videoId", default="", namespaces=NS)
        if not vid:
            continue
        title = entry.findtext("atom:title", default="", namespaces=NS)
        published = entry.findtext("atom:published", default="", namespaces=NS)
        group = entry.find("media:group", NS)
        desc, thumb = "", ""
        if group is not None:
            desc = group.findtext("media:description", default="", namespaces=NS)
            t = group.find("media:thumbnail", NS)
            if t is not None:
                thumb = t.get("url", "")
        link = f"https://www.youtube.com/watch?v={vid}"
        out.append({
            "id": make_id(src["id"], vid),
            "kind": "video",
            "title": clean(title),
            "url": link,
            "published": published,
            "thumbnail": thumb or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "text": clean(desc)[:TEXT_LIMIT],
            "text_basis": "영상 설명란",
            "youtube_id": vid,
        })
    return out


# ---------------- 공통: 상세 페이지 본문 추출 ----------------

def meta(soup: BeautifulSoup, *names: str) -> str:
    for n in names:
        tag = soup.find("meta", attrs={"property": n}) or soup.find("meta", attrs={"name": n})
        if tag and tag.get("content"):
            return tag["content"].strip()
    return ""


def main_text(soup: BeautifulSoup) -> str:
    for bad in soup(["script", "style", "noscript", "header", "footer", "nav", "form"]):
        bad.decompose()
    best, best_len = None, 0
    for el in soup.find_all(["article", "div", "section", "td"]):
        cls = " ".join(el.get("class", [])) + " " + (el.get("id") or "")
        if not re.search(r"(view|content|article|body|text|detail|cont)", cls, re.I):
            continue
        n = len(el.get_text(" ", strip=True))
        if n > best_len:
            best, best_len = el, n
    target = best or soup.body or soup
    return clean(target.get_text("\n", strip=True))


def youtube_in(soup: BeautifulSoup) -> str:
    for tag in soup.find_all(["iframe", "a"]):
        src = tag.get("src") or tag.get("href") or ""
        m = re.search(r"(?:youtube\.com/(?:embed/|watch\?v=)|youtu\.be/)([\w-]{11})", src)
        if m:
            return m.group(1)
    return ""


# ---------------- DBR ----------------

def collect_dbr(src: dict, limit: int) -> list[dict]:
    soup = BeautifulSoup(get(src["list_url"]).text, "html.parser")
    seen, links = set(), []
    for a in soup.find_all("a", href=True):
        href = urljoin(src["list_url"], a["href"])
        if "/article/view/" not in href:
            continue
        key = re.sub(r"[?#].*$", "", href)
        title = clean(a.get_text(" ", strip=True))
        if key in seen or len(title) < 4:
            continue
        seen.add(key)
        links.append((key, title))
        if len(links) >= limit:
            break
    out = []
    for url, title in links:
        item = {
            "id": make_id(src["id"], url),
            "kind": "article",
            "title": title,
            "url": url,
            "published": "",
            "thumbnail": "",
            "text": "",
            "text_basis": "기사 공개 부분",
        }
        try:
            d = BeautifulSoup(get(url).text, "html.parser")
            item["title"] = re.sub(r"\s*[|\-]\s*DBR\s*$", "", clean(meta(d, "og:title")) or title)
            item["thumbnail"] = meta(d, "og:image")
            item["published"] = meta(d, "article:published_time", "og:regDate", "date")
            lead = meta(d, "og:description", "description")
            body = main_text(d)
            item["text"] = clean(f"{lead}\n\n{body}")[:TEXT_LIMIT]
        except Exception as e:  # 상세 실패해도 제목은 남긴다
            item["text"] = ""
            item["detail_error"] = str(e)[:200]
        out.append(item)
        time.sleep(1)
    return out


# ---------------- 100주년기념교회 게시판 ----------------

ID_PARAMS = ("no", "idx", "uid", "num", "seq", "wr_id", "board_no", "bno", "id")


def board_key(href: str) -> str | None:
    q = parse_qs(urlparse(href).query)
    for p in ID_PARAMS:
        if p in q and q[p][0].isdigit():
            return f"{p}={q[p][0]}"
    return None


def collect_100church(src: dict, limit: int) -> list[dict]:
    html = get(src["list_url"]).text
    soup = BeautifulSoup(html, "html.parser")
    seen, links = set(), []
    for a in soup.find_all("a", href=True):
        href = urljoin(src["list_url"], a["href"])
        if "board=cast" not in href:
            continue
        key = board_key(href)
        title = clean(a.get_text(" ", strip=True))
        if not key or key in seen or len(title) < 2:
            continue
        seen.add(key)
        links.append((href, key, title))
        if len(links) >= limit:
            break
    if not links:  # 구조 파악용: 목록을 못 찾으면 원본 HTML을 남긴다
        dbg = ROOT / "data" / "debug"
        dbg.mkdir(parents=True, exist_ok=True)
        (dbg / "100church.html").write_text(html, encoding="utf-8")
    out = []
    for url, key, title in links:
        item = {
            "id": make_id(src["id"], key),
            "kind": "post",
            "title": title,
            "url": url,
            "published": "",
            "thumbnail": "",
            "text": "",
            "text_basis": "게시글 본문",
        }
        try:
            d = BeautifulSoup(get(url).text, "html.parser")
            vid = youtube_in(d)
            if vid:
                item["youtube_id"] = vid
                item["kind"] = "video"
                item["thumbnail"] = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
            item["thumbnail"] = item["thumbnail"] or meta(d, "og:image")
            lead = meta(d, "og:description", "description")
            item["text"] = clean(f"{lead}\n\n{main_text(d)}")[:TEXT_LIMIT]
        except Exception as e:
            item["detail_error"] = str(e)[:200]
        out.append(item)
        time.sleep(1)
    return out


COLLECTORS = {
    "youtube_channel": collect_youtube,
    "youtube_playlist": collect_youtube,
    "dbr": collect_dbr,
    "board_100church": collect_100church,
}


def main() -> int:
    config = json.loads(SOURCES.read_text(encoding="utf-8"))
    cats = config["categories"]
    store = {"updated": "", "items": []}
    if ITEMS.exists():
        store = json.loads(ITEMS.read_text(encoding="utf-8"))
    known = {it["id"]: it for it in store["items"]}
    seen_sources = {it["source"] for it in store["items"]}

    status = {"run_at": now_iso(), "sources": {}}
    added = 0
    for src in config["sources"]:
        if src.get("enabled") is False:
            continue
        limit = PER_RUN_PER_SOURCE if src["id"] in seen_sources else FIRST_RUN_PER_SOURCE
        try:
            found = COLLECTORS[src["type"]](src, limit)
            new = 0
            for it in found:
                if it["id"] in known:
                    continue
                it.update({
                    "source": src["id"],
                    "source_name": src["name"],
                    "category": src["category"],
                    "category_name": cats[src["category"]],
                    "collected_at": now_iso(),
                })
                known[it["id"]] = it
                new += 1
            added += new
            status["sources"][src["id"]] = {"ok": True, "found": len(found), "new": new}
            print(f"[ok] {src['name']}: {len(found)}개 확인, 새 글 {new}개")
        except Exception as e:
            status["sources"][src["id"]] = {"ok": False, "error": str(e)[:300]}
            print(f"[실패] {src['name']}: {e}", file=sys.stderr)

    items = sorted(known.values(), key=lambda x: x.get("collected_at", ""), reverse=True)[:MAX_ITEMS]
    ITEMS.parent.mkdir(parents=True, exist_ok=True)
    if added or not ITEMS.exists():
        store = {"updated": now_iso(), "items": items}
        ITEMS.write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
    STATUS.write_text(json.dumps(status, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"새 글 총 {added}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
