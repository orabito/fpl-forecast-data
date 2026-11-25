"""Builds referees.json from football-data.org (secret FOOTBALL_DATA_TOKEN).
Keeps names already published for 14 days after kickoff and always rewrites
updated_at. Prints a clear message for every failure."""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

OUT = "referees.json"
URL = "https://api.football-data.org/v4/competitions/PL/matches?status=SCHEDULED,TIMED"


def fail(msg):
    print("ERROR: " + msg)
    sys.exit(1)


token = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()
if not token:
    fail("secret FOOTBALL_DATA_TOKEN is empty or missing (Settings > Secrets and variables > Actions)")
print("token length:", len(token))  # length only, never the value

data = None
for attempt in range(1, 4):
    try:
        req = urllib.request.Request(URL, headers={"X-Auth-Token": token, "User-Agent": "fpl-forecast-feed"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        break
    except urllib.error.HTTPError as e:
        body = e.read()[:200].decode("utf-8", "replace")
        if e.code in (400, 401, 403):
            fail("football-data.org rejected the token (HTTP %d): %s. Check the secret value has no spaces or quotes." % (e.code, body))
        print("HTTP %d on attempt %d: %s" % (e.code, attempt, body))
    except Exception as e:  # network trouble
        print("attempt %d failed: %s" % (attempt, e))
    time.sleep(10 * attempt)
if data is None:
    fail("could not fetch football-data.org after 3 tries")

matches = data.get("matches", [])
now = datetime.now(timezone.utc)

old = []
if os.path.exists(OUT):
    try:
        old = json.load(open(OUT, encoding="utf-8")).get("referees", [])
    except Exception as e:
        print("note: old %s unreadable (%s), starting fresh" % (OUT, e))

keep = {}
for r in old:
    try:
        ko = datetime.fromisoformat(r["kickoff"].replace("Z", "+00:00"))
        if ko > now - timedelta(days=14):
            keep[(r["home"], r["away"], r["kickoff"])] = r
    except Exception:
        continue

for m in matches:
    refs = [x.get("name") for x in m.get("referees", []) if x.get("type") == "REFEREE" and x.get("name")]
    if not refs:
        continue
    h, a = m["homeTeam"], m["awayTeam"]
    keep[(h["name"], a["name"], m["utcDate"])] = {
        "home": h["name"], "home_tla": h.get("tla") or "",
        "away": a["name"], "away_tla": a.get("tla") or "",
        "kickoff": m["utcDate"], "referee": refs[0], "source": "football-data.org"}

out = {"updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
       "referees": sorted(keep.values(), key=lambda r: r["kickoff"])}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print("fetched %d upcoming matches, published %d referee names -> %s" % (len(matches), len(out["referees"]), os.path.abspath(OUT)))
