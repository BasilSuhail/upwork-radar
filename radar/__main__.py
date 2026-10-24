"""python -m radar serve | score [file] | history"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import core


def main() -> None:
    p = argparse.ArgumentParser(prog="radar")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="run the web page")
    s.add_argument("--host", default=os.environ.get("RADAR_HOST", "127.0.0.1"))
    s.add_argument("--port", type=int, default=int(os.environ.get("RADAR_PORT", "8787")))
    sc = sub.add_parser("score", help="score a job from a file or stdin")
    sc.add_argument("file", nargs="?")
    sc.add_argument("--url", default="")
    sub.add_parser("history", help="list scored jobs")
    a = p.parse_args()

    if a.cmd == "serve":
        from .web import serve
        serve(a.host, a.port)
    elif a.cmd == "score":
        text = open(a.file, encoding="utf-8").read() if a.file else sys.stdin.read()
        r = core.score_job(text, a.url)
        print(f"{r['score']}/10 {r['verdict'].upper()} [{r['niche']}] {r['title']}")
        for x in r["reasons"]:
            print(f"  + {x}")
        for x in r["red_flags"]:
            print(f"  ! {x}")
        if r["proposal"]:
            print("\n" + r["proposal"])
    else:
        for r in core.history():
            print(json.dumps({k: r[k] for k in ("id", "created", "score", "verdict", "status", "title")}))


if __name__ == "__main__":
    main()
