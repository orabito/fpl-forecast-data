"""Builds referees.json from football-data.org (needs FOOTBALL_DATA_TOKEN).
Runs in GitHub Actions. Keeps names it has already published (a feed hiccup
never erases a referee) and always rewrites updated_at, so the repo stays active."""
import json, os, sys, urllib.request
from datetime import datetime, timedelta, timezone

TOKEN = os.environ.get("FOOTBALL_DATA_TOKEN", "").strip()
if not TOKEN:
    sys.exit("FOOTBALL_DATA_TOKEN secret is missing")
OUT = "referees.json"
now = datetime.now(timezone.utc)

req = urllib.request.Request(
    "https://api.football-data.org/v4/competitions/PL/matches?status=SCHEDULED,TIMED",
    headers={"X-Auth-Token": TOKEN})
matches = json.load(urllib.request.urlopen(req, timeout=30))["matches"]

try:
    old = json.load(open(OUT))["referees"]
except Exception:
    old = []
keep = {}
for r in old:  # keep earlier names for 14 days after kickoff
    try:
        ko = datetime.fromisoformat(r["kickoff"].replace("Z", "+00:00"))
    except Exception:
        continue
    if ko > now - timedelta(days=14):
        keep[(r["home"], r["away"], r["kickoff"])] = r

for m in matches:
    refs = [x["name"] for x in m.get("referees", []) if x.get("type") == "REFEREE" and x.get("name")]
    if not refs:
        continue
    h, a = m["homeTeam"], m["awayTeam"]
    keep[(h["name"], a["name"], m["utcDate"])] = {
        "home": h["name"], "home_tla": h.get("tla") or "",
        "away": a["name"], "away_tla": a.get("tla") or "",
        "kickoff": m["utcDate"], "referee": refs[0], "source": "football-data.org"}

out = {"updated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
       "referees": sorted(keep.values(), key=lambda r: r["kickoff"])}
json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False)
print("published", len(out["referees"]), "referee names")
