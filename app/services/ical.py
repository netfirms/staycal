import time
import urllib.request
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional, Tuple

# Very small in-memory cache: url -> (fetched_at_epoch, events)
_cache: dict[str, Tuple[float, list[dict]]] = {}
_CACHE_TTL_SECONDS = 15 * 60  # 15 minutes


def _parse_ics_datetime(val: str) -> datetime:
    """
    Parse DTSTART/DTEND values. Supports formats like:
    - 20250105 (DATE)
    - 20250105T120000Z (UTC)
    - 20250105T120000 (local naive)
    Returns a datetime; date-only values become midnight.
    """
    v = val.strip()
    # Strip any trailing parameters like ;VALUE=DATE already handled by caller
    # Accept basic forms
    try:
        if len(v) == 8 and v.isdigit():
            return datetime.strptime(v, "%Y%m%d")
        if v.endswith("Z") and len(v) >= 16:
            return datetime.strptime(v, "%Y%m%dT%H%M%SZ")
        if "T" in v and len(v) >= 15:
            return datetime.strptime(v, "%Y%m%dT%H%M%S")
    except Exception:
        pass
    # Fallback: try to keep only date part
    try:
        return datetime.strptime(v[:8], "%Y%m%d")
    except Exception:
        # As last resort, use today
        return datetime.combine(date.today(), datetime.min.time())


def _normalize_dt_to_date(d: datetime) -> date:
    return d.date()


def _iter_lines(text: str):
    # ICS allows folded lines; unfold simple cases (lines starting with space are continuations)
    prev = None
    for raw in text.splitlines():
        if raw.startswith(" ") and prev is not None:
            prev += raw[1:]
        else:
            if prev is not None:
                yield prev
            prev = raw
    if prev is not None:
        yield prev


def _parse_events(ics_text: str) -> List[Dict]:
    events: List[Dict] = []
    in_event = False
    cur: Dict[str, str] = {}
    for line in _iter_lines(ics_text):
        line = line.strip()
        if line == "BEGIN:VEVENT":
            in_event = True
            cur = {}
            continue
        if line == "END:VEVENT":
            if in_event:
                # Build event
                dtstart_raw = cur.get("DTSTART") or cur.get("DTSTART;VALUE=DATE") or ""
                dtend_raw = cur.get("DTEND") or cur.get("DTEND;VALUE=DATE") or ""
                summary = cur.get("SUMMARY", "OTA Booking")
                if not dtstart_raw:
                    in_event = False
                    cur = {}
                    continue
                sdt = _parse_ics_datetime(dtstart_raw.split(":")[-1])
                if dtend_raw:
                    edt = _parse_ics_datetime(dtend_raw.split(":")[-1])
                else:
                    # If no DTEND, assume one day event
                    edt = sdt + timedelta(days=1)
                s = _normalize_dt_to_date(sdt)
                e = _normalize_dt_to_date(edt)
                # Ensure end is exclusive and at least +1 day if equal
                if e <= s:
                    e = s + timedelta(days=1)
                events.append({
                    "start_date": s,
                    "end_date": e,
                    "title": summary,
                })
            in_event = False
            cur = {}
            continue
        if in_event:
            # Split on first colon; left part may include parameters
            if ":" in line:
                key, val = line.split(":", 1)
                # Normalize key without params for common ones
                key_norm = key.split(";")[0].upper()
                cur[key_norm if key_norm in ("DTSTART", "DTEND", "SUMMARY") else key] = val.strip()
    return events


def fetch_ota_events(url: Optional[str]) -> List[Dict]:
    """Fetch and parse ICS events from the given URL.
    Returns list of dicts with keys: start_date (date), end_date (date), title (str).
    Uses a small in-memory cache to reduce network calls.
    """
    if not url:
        return []
    now = time.time()
    cached = _cache.get(url)
    if cached and (now - cached[0] < _CACHE_TTL_SECONDS):
        return cached[1]
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = resp.read()
            text = data.decode("utf-8", errors="ignore")
            events = _parse_events(text)
            _cache[url] = (now, events)
            return events
    except Exception:
        # Cache empty result briefly to avoid hammering on failures
        _cache[url] = (now, [])
        return []


def overlaps_ota(events: List[Dict], start: date, end: date) -> bool:
    """Return True if [start, end) overlaps any OTA event [s, e)."""
    for ev in events:
        s = ev.get("start_date")
        e = ev.get("end_date")
        if not s or not e:
            continue
        if s < end and e > start:
            return True
    return False
