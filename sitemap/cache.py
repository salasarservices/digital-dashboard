from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

_DATE_FMT = "%Y-%m-%dT%H:%M:%SZ"


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime(_DATE_FMT)


def _parse_dt(s: str) -> datetime:
    return datetime.strptime(s, _DATE_FMT).replace(tzinfo=timezone.utc)


def load_cache(path: str) -> dict[str, Any]:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_cache(records: dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2, ensure_ascii=False, sort_keys=True)


def is_fresh(record: dict[str, Any], max_age_days: int = 7) -> bool:
    ts = record.get("last_crawled_at")
    if not ts:
        return False
    age = datetime.now(timezone.utc) - _parse_dt(ts)
    return age.days < max_age_days


def upsert_record(cache: dict[str, Any], url: str, data: dict[str, Any]) -> None:
    cache[url] = {**data, "last_crawled_at": _now_utc()}


def append_run_log(entry: dict[str, Any], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({**entry, "run_at": _now_utc()}, ensure_ascii=False) + "\n")


def load_run_log(path: str) -> list[dict[str, Any]]:
    if not os.path.exists(path):
        return []
    runs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    runs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return runs
