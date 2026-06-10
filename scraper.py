#!/usr/bin/env python3
"""Fetch CUPL international cooperation notices and keep a daily history."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


BASE_URL = "https://globalstudy.cupl.edu.cn"
NOTICE_URL = BASE_URL + "/news"
API_URL = BASE_URL + "/api/news/query"
USER_AGENT = "Mozilla/5.0 (compatible; cupl-globalstudy-notice-watch/1.0; +https://github.com/houdemingfagewuzhigong)"
DATA_DIR = Path("data")


@dataclass
class Notice:
    id: str
    title: str
    date: str
    url: str
    summary: str
    section: str
    source_url: str
    first_seen_at: str
    last_seen_at: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def clean(text: str) -> str:
    text = re.sub(r"<script.*?</script>", "", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S | re.I)
    text = re.sub(r"<.*?>", "", text, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(text or "")).strip()


def notice_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url + "?" + query,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": NOTICE_URL,
            "X-Forwared-Method": "GET",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        body = response.read().decode("utf-8", "ignore")
    if body.lstrip().startswith("<"):
        raise RuntimeError("official API returned HTML instead of JSON, likely a site protection challenge")
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise RuntimeError("official API returned a non-object JSON payload")
    return payload


def normalize_record(record: dict[str, Any], section: str, source_url: str, seen_at: str) -> Notice | None:
    raw_id = record.get("id") or record.get("newsId")
    title = clean(str(record.get("title") or record.get("name") or ""))
    if not raw_id or not title:
        return None
    date_value = record.get("date") or record.get("createdAt") or record.get("createTime") or record.get("startTime") or ""
    date_match = re.search(r"\d{4}-\d{2}-\d{2}", str(date_value))
    date = date_match.group(0) if date_match else ""
    url = f"{BASE_URL}/news/{raw_id}"
    summary = clean(str(record.get("intro") or record.get("summary") or record.get("content") or ""))[:240]
    return Notice(
        id=notice_id(url),
        title=title,
        date=date,
        url=url,
        summary=summary,
        section=section,
        source_url=source_url,
        first_seen_at=seen_at,
        last_seen_at=seen_at,
    )


def extract_items(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    data = payload.get("data")
    total = payload.get("totalElements") or payload.get("total") or 0
    if isinstance(data, list):
        return data, int(total or len(data))
    if isinstance(data, dict):
        for key in ("content", "records", "items", "list"):
            value = data.get(key)
            if isinstance(value, list):
                return value, int(data.get("totalElements") or data.get("total") or total or len(value))
    return [], int(total or 0)


def fetch(max_pages: int = 3, page_size: int = 20) -> tuple[list[Notice], dict[str, str]]:
    seen_at = now_iso()
    notices: list[Notice] = []
    diagnostics: dict[str, str] = {}
    sections = [("通知公告", "notice"), ("新闻动态", "trend")]
    for section, classify in sections:
        for page in range(max_pages):
            params = {"page": page, "size": page_size, "newsClassify": classify}
            source_url = API_URL + "?" + urllib.parse.urlencode(params)
            try:
                payload = request_json(API_URL, params)
            except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, json.JSONDecodeError) as exc:
                diagnostics[section] = str(exc)
                break
            items, total = extract_items(payload)
            for item in items:
                notice = normalize_record(item, section, source_url, seen_at)
                if notice:
                    notices.append(notice)
            if not items or (page + 1) * page_size >= total:
                break
    unique = {notice.id: notice for notice in notices}
    return sorted(unique.values(), key=lambda item: (item.date, item.title), reverse=True), diagnostics


def load_existing() -> dict[str, Notice]:
    path = DATA_DIR / "notices.json"
    if not path.exists():
        return {}
    return {item["id"]: Notice(**item) for item in json.loads(path.read_text(encoding="utf-8"))}


def save(notices: list[Notice], diagnostics: dict[str, str]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "history").mkdir(exist_ok=True)
    existing = load_existing()
    merged = existing.copy()
    seen_at = now_iso()
    for notice in notices:
        if notice.id in merged:
            notice.first_seen_at = merged[notice.id].first_seen_at
        notice.last_seen_at = seen_at
        merged[notice.id] = notice
    rows = sorted(merged.values(), key=lambda item: (item.date, item.title), reverse=True)
    payload = [asdict(item) for item in rows]
    (DATA_DIR / "notices.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DATA_DIR / "history" / f"{dt.date.today().isoformat()}.json").write_text(json.dumps([asdict(item) for item in notices], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (DATA_DIR / "notices.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        fields = list(Notice.__dataclass_fields__.keys())
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(payload)
    meta = {
        "site": "中国政法大学国际合作与交流处出国境申请管理平台",
        "notice_url": NOTICE_URL,
        "api_url": API_URL,
        "updated_at": seen_at,
        "total_notices": len(rows),
        "sections": ["通知公告", "新闻动态"],
        "latest_date": rows[0].date if rows else None,
        "diagnostics": diagnostics,
        "disclaimer": "非官方项目，仅归档公开网页信息，不代表中国政法大学官方。",
    }
    (DATA_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    notices, diagnostics = fetch(max_pages)
    save(notices, diagnostics)
    print(f"fetched {len(notices)} notices from CUPL international cooperation API")
    if notices:
        print(f"latest: {notices[0].date} {notices[0].title}")
    if diagnostics:
        print("diagnostics:", json.dumps(diagnostics, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
