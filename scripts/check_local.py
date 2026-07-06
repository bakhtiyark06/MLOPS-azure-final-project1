#!/usr/bin/env python3
# Author: TODO - Team Member Name
# Responsibility: TODO - Local Dev Utilities
# Last Reviewed: TODO

"""Quick check: is the local outage API running?"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request


def check(port: int = 8000) -> int:
    for host in ("127.0.0.1", "localhost"):
        url = f"http://{host}:{port}/health"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                body = json.loads(resp.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            print(f"  {url}  ->  NOT RUNNING ({exc})")
            continue

        if body.get("feature_count") == 7:
            print(f"  {url}  ->  OK (Website Outage Predictor)")
            print(f"\nOpen in browser: http://{host}:{port}/docs")
            return 0
        print(f"  {url}  ->  WRONG APP (not outage project): {body}")
        return 1

    print("\nServer is not running. Start it with:")
    print("  python3.11 scripts/run_local.py")
    print(f"  python3.11 scripts/run_local.py --port {port}")
    return 1


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    raise SystemExit(check(port))
