#!/usr/bin/env python3
"""Refresh broadcast episode metadata; preserve verified crossover order."""
import json, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

SHOWS={"Fire":"Chicago Fire","Med":"Chicago Med","P.D.":"Chicago P.D."}
OUT=Path(__file__).resolve().parents[1]/"data"
OUT.mkdir(exist_ok=True)
now=datetime.now(timezone.utc)
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"OneChicagoWatchTracker/1.0 (GitHub Pages; TVmaze public API)"})
    with urllib.request.urlopen(req,timeout=30) as res:
        return json.load(res)

rows=[]
for key,name in SHOWS.items():
    url="https://api.tvmaze.com/singlesearch/shows?q="+urllib.parse.quote(name)
    show=get(url)
    for ep in get(f"https://api.tvmaze.com/shows/{show['id']}/episodes"):
        if ep.get("number") is None or ep.get("season") is None: continue
        aired=(ep.get("airstamp") or "")
        if not aired: continue
        try: is_aired=datetime.fromisoformat(aired.replace("Z","+00:00"))<=now
        except ValueError: continue
        if not is_aired: continue
        s,n=ep["season"],ep["number"]
        rows.append({"id":f"{key} S{s:02d}E{n:02d}","show":key,"code":f"S{s:02d}E{n:02d}",
                    "title":ep.get("name") or "", "airdate":ep.get("airdate") or "",
                    "airstamp":aired,"crossover":False,"note":""})

# Crossover chapters are ordered by story, even when broadcast times differ.
GROUPS=[
["Fire S02E20","P.D. S01E12"],
["Fire S03E07","P.D. S02E07"],
["Fire S03E13","P.D. S02E13"],
["Fire S03E21","P.D. S02E20"],
["Fire S04E10","Med S01E05","P.D. S03E10"],
["Fire S05E09","P.D. S04E09"],
["P.D. S05E16","Fire S06E13"],
["Fire S07E02","Med S04E02","P.D. S06E02"],
["Fire S07E15","P.D. S06E15"],
["Fire S08E04","Med S05E04","P.D. S07E04"],
["Fire S08E15","P.D. S07E15"],
["Fire S13E11","Med S10E11","P.D. S12E11"],
["Fire S14E13","Med S11E13","P.D. S13E13"],
]
byid={e["id"]:e for e in rows}
groups=[]
for group in GROUPS:
    if all(x in byid for x in group):
        groups.append(group)
        for i,x in enumerate(group):
            byid[x]["crossover"]=True
            byid[x]["note"]=f"★ CROSSOVER: Part {i+1}/{len(group)}"
            byid[x]["crossoverGroup"]=group[0]
# Group relevant chapters at the earlier airing position to keep the story continuous.
seen=set()
chunks=[]
for e in rows:
    if e["id"] in seen: continue
    group=next((g for g in groups if e["id"] in g),None)
    if group:
        key=min(byid[x]["airstamp"] for x in group)
        chunks.append((key,1,[byid[x] for x in group]))
        seen.update(group)
    else:
        chunks.append((e["airstamp"],0,[e]))
        seen.add(e["id"])
chunks.sort(key=lambda t:(t[0],t[1]))
ordered=[episode for _,_,chunk in chunks for episode in chunk]
data={"generatedAt":now.isoformat(),"source":"TVmaze","episodes":ordered,
      "notes":"Broadcast chronology with verified major crossover sequences kept together. Some standalone in-universe chronology is ambiguous."}
(OUT/"episodes.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
print("Updated",len(ordered),"episodes",len(groups),"crossover events.")
