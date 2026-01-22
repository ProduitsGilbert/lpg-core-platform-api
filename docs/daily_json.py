from __future__ import annotations

import argparse
import datetime as dt
import json
from typing import Optional

from planner_daily_report.cli import _parse_date, load_env_file
from planner_daily_report.service import generate_daily_planner_report


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="planner_daily_report.export_json")
    p.add_argument("--env-file", default=".env", help="Path to .env (default: .env). Use '' to disable.")
    p.add_argument("--env-override", action="store_true", help="Override env vars with .env values")
    p.add_argument("--date", default="yesterday", help="YYYY-MM-DD or 'yesterday' (last business day)")
    p.add_argument("--tasklist-filter", default=None, help="Optional extra OData filter for task list")
    p.add_argument("--out", default=None, help="Write JSON to a file path instead of stdout")
    args = p.parse_args(argv)

    if args.env_file:
        load_env_file(args.env_file, override=bool(args.env_override))

    posting_date: dt.date = _parse_date(args.date)
    payload = generate_daily_planner_report(posting_date=posting_date, tasklist_filter=args.tasklist_filter)
    s = json.dumps(payload, ensure_ascii=False, indent=2)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(s)
            f.write("\n")
        print(f"Wrote: {args.out}")
        return 0

    print(s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


