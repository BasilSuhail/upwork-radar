"""Score a pasted job, draft a proposal, keep the history in SQLite."""
from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from . import llm

HOME = Path(os.environ.get("RADAR_HOME", "~/.upwork-radar")).expanduser()
PROFILE = HOME / "profile.md"
DB = HOME / "radar.db"
MODEL = os.environ.get("RADAR_MODEL", "haiku")

SYSTEM = """You screen Upwork jobs for one freelancer and draft proposals they send by hand.

FREELANCER PROFILE:
{profile}

TASK: read the job the user pastes and answer with ONE JSON object, no markdown, no other text:
{{
  "title": "job title, from the post or a short summary",
  "score": 0-10 integer, how likely this freelancer wins AND does the job well,
  "verdict": "apply" | "maybe" | "skip",
  "niche": "ai-automation" | "power-bi" | "python-fullstack" | "other",
  "reasons": ["max 3 short reasons for the score"],
  "red_flags": ["client or job risks: unverified payment, tiny budget, vague scope, off-platform contact, test work for free, too many proposals; empty if none"],
  "proposal": "the proposal text, or empty string when verdict is skip"
}}

SCORING: 8-10 = core niche, clear scope, fair budget, healthy client. 5-7 = partial fit or some risk.
0-4 = outside the niches (bookkeeping, tax, data entry, design...), scam signs, or needs skills not in the profile.

PROPOSAL RULES (only when verdict is apply or maybe):
- Under 170 words. Plain text, short paragraphs, no headings, no "Dear Sir/Madam", no "I am writing to".
- First two lines are the preview the client sees: restate their exact problem and how it gets solved.
- Then 1-2 concrete proof points from the profile that match this job, with numbers.
- Then a short plan: 2-4 steps or a first milestone.
- Answer any question the client asked in the post. If the post asks for a keyword or code word, include it.
- End with one specific question about their setup, then the freelancer's first name.
- Never invent experience, clients, certificates or tools not in the profile. UK English.
"""

JSON_RE = re.compile(r"\{.*\}", re.S)


def load_profile() -> str:
    if not PROFILE.exists():
        raise FileNotFoundError(f"Profile missing: {PROFILE} (see RADAR.md)")
    return PROFILE.read_text(encoding="utf-8")


def parse(raw: str) -> dict:
    m = JSON_RE.search(raw)
    if not m:
        raise ValueError(f"No JSON in model reply: {raw[:200]}")
    data = json.loads(m.group(0), strict=False)
    data["score"] = max(0, min(10, int(data.get("score", 0))))
    if data.get("verdict") not in ("apply", "maybe", "skip"):
        data["verdict"] = "apply" if data["score"] >= 7 else "maybe" if data["score"] >= 5 else "skip"
    data.setdefault("title", "")
    data.setdefault("niche", "other")
    data["reasons"] = list(data.get("reasons") or [])
    data["red_flags"] = list(data.get("red_flags") or [])
    data["proposal"] = data.get("proposal") or ""
    return data


def connect() -> sqlite3.Connection:
    HOME.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY,
        created TEXT NOT NULL,
        url TEXT,
        job_text TEXT NOT NULL,
        title TEXT,
        score INTEGER,
        verdict TEXT,
        niche TEXT,
        result_json TEXT,
        status TEXT NOT NULL DEFAULT 'new'
    )""")
    return con


def score_job(job_text: str, url: str = "", ask=llm.ask) -> dict:
    job_text = job_text.strip()
    if not job_text:
        raise ValueError("Empty job text")
    system = SYSTEM.format(profile=load_profile())
    result = parse(ask(system, f"JOB POST:\n{job_text}", model=MODEL))
    with connect() as con:
        cur = con.execute(
            "INSERT INTO jobs (created, url, job_text, title, score, verdict, niche, result_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), url.strip(), job_text,
             result["title"], result["score"], result["verdict"], result["niche"], json.dumps(result)))
        result["id"] = cur.lastrowid
    return result


def history(limit: int = 50) -> list[dict]:
    with connect() as con:
        rows = con.execute("SELECT id, created, url, title, score, verdict, niche, status, result_json"
                           " FROM jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d.update(json.loads(d.pop("result_json") or "{}"))
        d["status"] = r["status"]
        out.append(d)
    return out


def set_status(job_id: int, status: str) -> None:
    if status not in ("new", "sent", "ignored"):
        raise ValueError(f"Bad status: {status}")
    with connect() as con:
        con.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
