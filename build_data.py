#!/usr/bin/env python3
"""
Regenerate data.js for the PoE2 Craft Planner from Craft of Exile's live dataset.

Run this whenever PoE2 gets a patch and the mods/weights change:
    python3 build_data.py

It downloads Craft of Exile's PoE2 data file, extracts every gear base's
prefix/suffix pool (with real spawn weights, tiers, tags and Essence mappings),
and writes data.js — which index.html loads. No API key needed.
"""
import json, re, urllib.request

URL = "https://www.craftofexile.com/json/poe2/main/poec_data.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
GEAR_GROUPS = {"1", "2", "3", "4", "5", "6", "7", "8"}  # jewellery, body, boots, helmets, gloves, 1h, 2h, offhand
JEWEL_GROUP = "9"   # Emerald / Ruby / Sapphire — capped at 2 prefix + 2 suffix; 5th mod via Vaal corruption
# Desecrated mods (Well of Souls) live in mgroup "10"; faction is a special mtype id.
DESEC_MGROUP = "10"
FACTION_MTYPE = {"39": "Amanamu", "40": "Kurgal", "41": "Ulaman"}  # defensive / ailment / offensive

def truthy(x): return str(x) in ("1", "true", "True")

def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    raw = urllib.request.urlopen(req, timeout=90).read().decode("utf-8")
    return json.loads(raw[raw.index("{"):])           # strip the "poecd=" JS wrapper

def fmt(v):
    def n(x):
        x = float(x); return str(int(x)) if x == int(x) else str(x)
    if isinstance(v, list):
        return n(v[0]) if len(v) == 1 else f"{n(v[0])}–{n(v[1])}"
    return n(v)

def fill(name, nvalues):
    try: vals = nvalues if isinstance(nvalues, list) else json.loads(nvalues)
    except Exception: vals = []
    i = 0
    def repl(_):
        nonlocal i
        s = fmt(vals[i]) if i < len(vals) else "#"; i += 1; return s
    return re.sub(r"#", repl, name)

def build(d):
    mind = d["modifiers"]["ind"]; mseq = d["modifiers"]["seq"]
    mod = lambda mid: mseq[mind[str(mid)]] if str(mid) in mind else None
    mtype_name = {m["id_mtype"]: m["name_mtype"] for m in d["mtypes"]["seq"]}
    tiers = d["tiers"]; basemods = d["basemods"]

    essmap = {}
    for e in d["essences"]["seq"]:
        nm = e.get("name_essence") or ""; t = e.get("tiers")
        if not t: continue
        try: tj = json.loads(t) if isinstance(t, str) else t
        except Exception: continue
        for base_id, arr in tj.items():
            for grp in arr:
                for entry in grp:
                    mid = entry.get("mod")
                    if not mid: continue
                    k = (str(base_id), str(mid))
                    if k not in essmap or (nm.startswith("Essence of") and not essmap[k].startswith("Essence of")):
                        essmap[k] = nm

    def as_int(x):
        try: return int(float(x))
        except Exception: return 0

    bases = [b for b in d["bases"]["seq"]
             if str(b.get("id_bgroup")) in (GEAR_GROUPS | {JEWEL_GROUP}) and not truthy(b.get("is_legacy"))]
    out = {}
    for b in bases:
        bid = str(b["id_base"]); mods = []; seen = set()
        for mid in basemods.get(bid, []):
            m = mod(mid)
            if not m or m.get("affix") not in ("prefix", "suffix") or m.get("id_mgroup") not in ("1", DESEC_MGROUP):
                continue
            tl = tiers.get(str(mid), {}).get(bid)
            if not tl or mid in seen: continue
            # Build the full tier ladder, best (highest ilvl) first = T1.
            ladder = sorted(tl, key=lambda t: as_int(t.get("ilvl")), reverse=True)
            tiers_out = []
            for idx, t in enumerate(ladder):
                w = as_int(t.get("weighting"))
                if w <= 0: continue
                tiers_out.append({"t": f"T{idx+1}", "ilvl": as_int(t.get("ilvl")),
                                  "weight": w, "val": fill(m["name_modifier"], t.get("nvalues"))})
            if not tiers_out: continue
            seen.add(mid)
            mtids = (m.get("mtypes") or "").split("|")
            tags = [mtype_name.get(t, "").lower() for t in mtids if t in mtype_name]
            try: fam = (json.loads(m.get("modgroups") or "[]") or [None])[0]
            except Exception: fam = None
            entry = {"id": mid, "name": m["name_modifier"], "type": m["affix"], "group": fam,
                     "tags": tags, "essence": essmap.get((bid, str(mid))), "tiers": tiers_out}
            if m.get("id_mgroup") == DESEC_MGROUP:           # desecrated (Well of Souls) mod
                entry["des"] = True
                fac = next((FACTION_MTYPE[t] for t in mtids if t in FACTION_MTYPE), None)
                entry["faction"] = fac
            mods.append(entry)
        if len(mods) >= 6:
            # sort prefixes first, then by the top tier's spawn weight (commonness)
            mods.sort(key=lambda x: (x["type"] != "prefix", -x["tiers"][0]["weight"]))
            out[bid] = {"name": b["name_base"], "mods": mods}
            if str(b.get("id_bgroup")) == JEWEL_GROUP:
                out[bid]["jewel"] = True
    return {k: out[k] for k in sorted(out, key=lambda k: out[k]["name"])}

# ---- Time-Lost (rare timeless) jewels — Craft of Exile lacks them, so pull from poe2db ----
import html as _html
PO2DB_TL = ["Time-Lost_Emerald", "Time-Lost_Sapphire", "Time-Lost_Ruby", "Time-Lost_Diamond"]

def _extract_array(h, key):
    i = h.find('"%s":[' % key)
    if i < 0: return None
    start = h.index('[', i); depth = 0; instr = False; esc = False
    for j in range(start, len(h)):
        c = h[j]
        if instr:
            if esc: esc = False
            elif c == '\\': esc = True
            elif c == '"': instr = False
        else:
            if c == '"': instr = True
            elif c == '[': depth += 1
            elif c == ']':
                depth -= 1
                if depth == 0: return h[start:j + 1]
    return None

def _clean_tl(s):
    s = re.sub(r'<span class="ndash">[^<]*</span>', '-', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = _html.unescape(s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s*local jewel effect.*$', '', s)   # strip hidden radius metadata
    s = re.sub(r'\s*\[\d+\]\s*$', '', s)
    return s

def fetch_timeless():
    def ai(x):
        try: return int(float(x))
        except Exception: return 1
    out = {}
    for slug in PO2DB_TL:
        try:
            req = urllib.request.Request("https://poe2db.tw/us/" + slug,
                headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
            h = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
            arr = _extract_array(h, "normal")
            if not arr:
                print(f"  {slug}: no mod data, skipped"); continue
            mods = json.loads(arr)
            mlist = []
            for i, m in enumerate(mods):
                val = _clean_tl(m.get("str", ""))
                if not val: continue
                typ = "prefix" if str(m.get("ModGenerationTypeID")) == "1" else "suffix"
                fam = (m.get("ModFamilyList") or [None])[0]
                mlist.append({"id": f"{slug}_{i}", "name": val, "type": typ, "tags": [], "group": fam,
                              "essence": None, "jewel": True,
                              "tiers": [{"t": "T1", "ilvl": ai(m.get("Level")),
                                         "weight": max(1, ai(m.get("DropChance"))), "val": val}]})
            if len(mlist) >= 4:
                mlist.sort(key=lambda x: (x["type"] != "prefix", -x["tiers"][0]["weight"]))
                out[slug] = {"name": slug.replace("_", " "), "mods": mlist, "jewel": True, "timeless": True}
                print(f"  + {slug.replace('_',' ')}: {len(mlist)} mods")
        except Exception as e:
            print(f"  {slug}: failed ({e})")
    return out


if __name__ == "__main__":
    print("Downloading Craft of Exile PoE2 dataset…")
    data = build(fetch())
    print("Downloading Time-Lost jewels from poe2db…")
    try:
        data.update(fetch_timeless())
        data = {k: data[k] for k in sorted(data, key=lambda k: data[k]["name"])}
    except Exception as e:
        print("Time-Lost fetch skipped:", e)
    js = "/* PoE2 0.5.x mod data — generated by build_data.py from Craft of Exile (craftofexile.com). */\n"
    js += "const BASES = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    open("renderer/data.js", "w").write(js)
    total = sum(len(v["mods"]) for v in data.values())
    print(f"Wrote data.js — {len(data)} bases, {total} modifiers.")
