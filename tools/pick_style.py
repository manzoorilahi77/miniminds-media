#!/usr/bin/env python3
"""Pick today's poster-studio style and theme for one Instagram item.

The Morning Planner runs this in its cloud sandbox (the file lives in the
miniminds-media repo, which the Planner clones) once per Instagram item, so the
rotation is the same arithmetic every day instead of a judgment call.

    python3 tools/pick_style.py --date 2026-10-24 --book 26 --format reel \
        --history history.json [--planned quiz-show:space] [--rejected escape-room]

history.json is a list of the recent Instagram rows of the Approval Board, newest
last: [{"date": "2026-10-23", "item": "20", "visual": "<the Visual links cell>"}].
The style and theme of a past item are read from its Visual links: the
"TO RENDER (poster studio): style=<id>, theme=<kit>" line before rendering, and
the "style-<id>_theme-<kit>" part of the media file names after rendering.

Rules (prompts/POST-REDESIGN-10-STYLES.md, Phase 3):
  - only styles that cover the book's category, minus any the owner rejected;
  - no style used in the last 5 Instagram items;
  - no style + theme pair used in the last 14 days;
  - UGC styles: 1 or 2 in any 7 days and never two in a row (when the last 7
    days have none, a UGC style is picked if one is allowed);
  - the pick among what is left is seeded by the date, the item and the book.
Five styles cannot avoid all of the last 5 for long (a category with four
styles never can), so when nothing passes, the no-repeat window shrinks from 5
to 4, 3, 2 and 1 items before the 14-day style + theme rule is relaxed. The
output says which rule gave.
Books outside word scramble, missing vowel and cryptogram print
{"style": null}: they keep today's poster-studio templates.
Prints one line of JSON."""
import argparse, datetime, hashlib, json, re, sys

# All ten approved by the owner on 23 Oct 2026 (five game, five UGC). Same ids and
# coverage as the renderer's formats.STYLES; a new style goes in both places.
STYLES = {
    "game-level":  dict(family="game", cats=["word-scramble", "missing-vowel"]),
    "quiz-show":   dict(family="game", cats=["word-scramble", "missing-vowel", "cryptogram"]),
    "board-game":  dict(family="game", cats=["word-scramble", "missing-vowel", "cryptogram"]),
    "escape-room": dict(family="game", cats=["cryptogram", "word-scramble"]),
    "quest-map":   dict(family="game", cats=["word-scramble", "missing-vowel", "cryptogram"]),
    "ugc-table-flatlay": dict(family="ugc", cats=["word-scramble", "missing-vowel", "cryptogram"]),
    "ugc-pov-text":      dict(family="ugc", cats=["word-scramble", "missing-vowel", "cryptogram"]),
    "ugc-solve-along":   dict(family="ugc", cats=["word-scramble", "missing-vowel", "cryptogram"]),
    "ugc-notes-app":     dict(family="ugc", cats=["word-scramble", "missing-vowel", "cryptogram"]),
    "ugc-whiteboard":    dict(family="ugc", cats=["word-scramble", "missing-vowel", "cryptogram"]),
}
# The renderer's themes.BOOK_KIT for the books in scope; "holiday" follows the US month.
BOOKS = {14: ("missing-vowel", "animals"), 15: ("missing-vowel", "school"), 16: ("missing-vowel", "food"),
         17: ("missing-vowel", "world"), 18: ("missing-vowel", "holiday"),
         24: ("word-scramble", "food"), 25: ("word-scramble", "holiday"), 26: ("word-scramble", "space"),
         27: ("word-scramble", "sports"), 28: ("word-scramble", "animals"),
         29: ("cryptogram", "journal"), 30: ("cryptogram", "museum"), 31: ("cryptogram", "map"), 33: ("cryptogram", "detective")}
SEASON = {1: "winter", 2: "valentine", 3: "spring", 4: "spring", 5: "spring", 6: "summer", 7: "summer", 8: "summer",
          9: "harvest", 10: "halloween", 11: "harvest", 12: "christmas"}
RE_STYLE = re.compile(r"style[=-]([a-z]+(?:-[a-z]+)*?)(?:[,_\s]|$)")
RE_THEME = re.compile(r"theme[=-]([a-z]+)")

def theme_for(book, date):
    kit = BOOKS[book][1]
    return SEASON[date.month] if kit == "holiday" else kit

def read(history):
    """(date, style, theme) for every past item whose Visual links name a style."""
    out = []
    for row in history:
        txt = str(row.get("visual", ""))
        s, t = RE_STYLE.search(txt), RE_THEME.search(txt)
        if s and s.group(1) in STYLES:
            out.append((str(row.get("date", "")), s.group(1), t.group(1) if t else ""))
        else:
            out.append((str(row.get("date", "")), None, None))       # an older post without a style
    return out

def pick(date, book, fmt, history, planned=(), rejected=(), item=""):
    if book not in BOOKS:
        return dict(style=None, why="this book keeps today's poster-studio template (styles cover word scramble, missing vowel and cryptogram only)")
    cat = BOOKS[book][0]; theme = theme_for(book, date)
    past = read(history) + [(date.isoformat(), s, t) for s, t in planned]
    cands = sorted(s for s, v in STYLES.items() if cat in v["cats"] and s not in rejected)
    if not cands:
        return dict(style=None, why=f"every style for {cat} is rejected in Rules Learned")
    since = (date - datetime.timedelta(days=14)).isoformat()
    pairs = {(s, t) for d, s, t in past if s and d >= since}
    week = (date - datetime.timedelta(days=7)).isoformat()
    ugc_week = sum(1 for d, s, _ in past if s and d >= week and STYLES[s]["family"] == "ugc")
    prev = next((s for _, s, _ in reversed(past) if s), None)
    styled = [s for _, s, _ in past if s]
    def allowed(c, k, keep_pairs):
        if c in styled[-k:]: return False
        if keep_pairs and (c, theme) in pairs: return False
        if STYLES[c]["family"] == "ugc" and (ugc_week >= 2 or (prev and STYLES[prev]["family"] == "ugc")): return False
        return True
    seed = int(hashlib.sha256(f"{date.isoformat()}|{item}|{book}|{fmt}".encode()).hexdigest(), 16)
    want_ugc = ugc_week == 0 and not (prev and STYLES[prev]["family"] == "ugc")
    # Five styles cannot keep "none of the last 5" for long, so the window
    # shrinks one item at a time before anything else gives; the 14-day
    # style + theme rule is kept as long as any style can satisfy it.
    for keep_pairs in (True, False):
        for k in (5, 4, 3, 2, 1):
            ok = [c for c in cands if allowed(c, k, keep_pairs)]
            if want_ugc and any(STYLES[c]["family"] == "ugc" for c in ok):
                ok = [c for c in ok if STYLES[c]["family"] == "ugc"]      # the week has no UGC post yet
            if ok:
                s = ok[seed % len(ok)]
                why = (f"picked from {ok} for {cat}: not used in the last {k} Instagram items"
                       + (", style + theme not used in 14 days" if keep_pairs else ", 14-day style + theme rule relaxed (nothing else was left)")
                       + (f"; rejected {sorted(rejected)}" if rejected else ""))
                break
        else:
            continue
        break
    else:
        age = {c: max([i for i, x in enumerate(styled) if x == c] or [-1]) for c in cands}
        s = min(cands, key=lambda c: (age[c], c))
        why = f"only one style is left for {cat}, so it repeats ({s})"
    return dict(style=s, theme=theme, category=cat,
                line=f"TO RENDER (poster studio): style={s}, theme={theme}, format={fmt}, book_id={book}, ", why=why)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True); ap.add_argument("--book", type=int, required=True)
    ap.add_argument("--format", required=True, choices=["single", "carousel", "reel"])
    ap.add_argument("--item", default=""); ap.add_argument("--history", default="")
    ap.add_argument("--planned", action="append", default=[], help="style:theme already picked today, in order")
    ap.add_argument("--rejected", default="", help="comma-separated style ids the owner rejected")
    a = ap.parse_args()
    hist = json.load(open(a.history)) if a.history else []
    planned = [tuple(p.split(":", 1)) if ":" in p else (p, "") for p in a.planned]
    rejected = {x.strip() for x in a.rejected.split(",") if x.strip()}
    print(json.dumps(pick(datetime.date.fromisoformat(a.date), a.book, a.format, hist, planned, rejected, a.item)))

if __name__ == "__main__":
    sys.exit(main())
