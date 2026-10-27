#!/usr/bin/env python3
"""Comment word of the day for every Instagram post (owner decision 27 Oct 2026).

Ten short words, one per US Eastern date, each used once per 10-day cycle. The order is
reshuffled for every new cycle, and a cycle never opens with the word the last one ended on.
Deterministic from the date, so nothing is stored; the Planner and the renderer get the same word.

   python3 pick_word.py                 today's word (US Eastern date)
   python3 pick_word.py 2026-11-03      that day's word
   python3 pick_word.py 2026-11-03 --week   that day and the next 9, with the cycle number

The posts say "Comment <WORD> + your answer". Nothing happens automatically when someone comments."""
import datetime, random, sys
from zoneinfo import ZoneInfo

WORDS = ["CRACKED", "GOTIT", "GENIUS", "BOOM", "AHA", "CHAMP", "WHIZ", "SOLVED", "SMARTY", "YES"]
START = datetime.date(2026, 10, 28)           # cycle 0 starts here

def order(cycle):
    """The ten words in the order cycle `cycle` uses them."""
    seed = 0
    while True:
        w = WORDS[:]; random.Random(cycle * 1000 + seed).shuffle(w)
        if cycle <= 0 or w[0] != order(cycle - 1)[-1]:
            return w
        seed += 1

def word_for(day):
    n = (day - START).days
    return order(n // 10)[n % 10]

def today_et():
    return datetime.datetime.now(ZoneInfo("America/New_York")).date()

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    day = datetime.date.fromisoformat(args[0]) if args else today_et()
    if "--week" in sys.argv:
        for i in range(10):
            d = day + datetime.timedelta(days=i)
            print(d, f"cycle {(d - START).days // 10}", word_for(d))
    else:
        print(word_for(day))
