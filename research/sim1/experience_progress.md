# Experience data — progress (3 Nov 2026 AEST)

Source: Leaguepedia Cargo export (https://lol.fandom.com/wiki/Special:CargoExport), read 3 Nov.

## Done
- Worlds and MSI winners before 2026, with rosters (TournamentResults Place_Number=1 + TournamentPlayers for that roster page and team).
  Worlds: 2011 Fnatic (Season 1), 2012 Taipei Assassins (Season 2), 2013 SK Telecom T1 (Season 3), 2014 Samsung White, 2015 SKT, 2016 SKT,
  2017 Samsung Galaxy, 2018 Invictus Gaming, 2019 FunPlus Phoenix, 2020 DAMWON, 2021 EDward Gaming, 2022 DRX, 2023 T1, 2024 T1, 2025 T1.
  MSI: 2015 EDG, 2016 SKT, 2017 SKT, 2018 RNG, 2019 G2, 2021 RNG, 2022 RNG, 2023 JDG, 2024 Gen.G, 2025 Gen.G.
  Rosters include coaches and subs; coaches must be dropped (Role = Coach). The Season 1 qualifier rows (Europe, North America) must be dropped.
  Faker: Worlds titles 2013, 2015, 2016, 2023, 2024, 2025 (6); MSI 2016, 2017 (2). Matches Luke's "6x".
- International games before 2026 (ScoreboardPlayers, Worlds + MSI pages, grouped by Link): 703 players. Faker 301 games over 18 events;
  Worlds appearances 9 (153 Worlds games). Keria 186 games, 11 events; Worlds appearances 6 (97 games).
  Note: the "year" key used SUBSTRING(OverviewPage,1,4), so the Season 1-3 Worlds all count as one appearance ("Seas"). Fix when re-pulling.
- Leaguepedia 2026 player-team records (ScoreboardPlayers from 1 Jan 2026, grouped Link/Name/Team): 5,957 rows. Faker/T1 = 160 games (file: 160).

## Not done (browser tool returned "Policy check temporarily unavailable" repeatedly)
- Matching the file's 442 players (489 player-team pairs, scratchpad/s1/oe_pairs.json) to Leaguepedia Links:
  rule = same name and same team (names/teams lower-cased, disambiguation in brackets removed); fallback = name unique across all 2026 records;
  list ambiguous and unmatched for review.
- Attaching titles / international games / Worlds appearances per player; spot-check Faker, Keria, Knight, Kiin pages.
- Re-pull needed: the browser-held results (window.__titles, __intl, __worlds, __lp26) are lost if the tab closes; the queries are quick to re-run.
