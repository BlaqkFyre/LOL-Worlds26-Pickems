"""The two test splits, with leak checks built in (14 Nov 2026; Luke: Worlds first, day by day).
  worlds_by_day(df)  yields (day, train, test): train = every row before that Worlds day, test = that day's Worlds rows
  fixed_2026(df)     (train, test): train before config.SPLIT, test = non-Worlds rows from config.SPLIT
  tuning(df)         (train, judge): train before config.TUNE_FROM, judge = TUNE_FROM..SPLIT (settings are chosen only here)
Each split asserts that no training row is on or after its test start."""
from . import config

def _guard(train, start, day):
    if len(train) and train[day].max() >= start: raise AssertionError(f"leak: training row on {train[day].max()} >= test start {start}")

def worlds_by_day(df, day="day", league="league"):
    for d in sorted(df.loc[df[league] == "WLDs", day].unique()):
        tr, te = df[df[day] < d], df[(df[day] == d) & (df[league] == "WLDs")]; _guard(tr, d, day)
        yield d, tr, te

def fixed_2026(df, day="day", league="league"):
    tr, te = df[df[day] < config.SPLIT], df[(df[day] >= config.SPLIT) & (df[league] != "WLDs")]; _guard(tr, config.SPLIT, day)
    return tr, te

def tuning(df, day="day"):
    tr, ju = df[df[day] < config.TUNE_FROM], df[(df[day] >= config.TUNE_FROM) & (df[day] < config.SPLIT)]; _guard(tr, config.TUNE_FROM, day)
    return tr, ju
