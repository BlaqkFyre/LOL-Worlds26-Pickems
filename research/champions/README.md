# Champion database (14 Nov 2026)

One row per champion (173), built by `build_champion_db.py` (run from the repo root; it uses `research/lib`, so every run leaves a record in `research/runs/`). Outputs: `champions.csv` (one row per champion) and `champions.json` (the same rows plus sources and rules). For the draft work and Luke's other project.

**Sources**
- **Riot client data** via the League wiki's champion data module (https://wiki.leagueoflegends.com/en-us/Module:ChampionData/data), read 14 Nov 2026 in the browser pane (the wiki blocks scripts) and saved to `research/local/champions/wiki_championdata_2026-11-14.txt`. All 175 lines were checked against per-line fingerprints computed in the browser. The two form rows (Mega Gnar, Kled & Skaarl) are left out.
- **Pro play** from the Oracle's Elixir 2026 file: major leagues, with the Worlds qualifier rows before 1 Oct left out. Worlds is 94 games on patch 16.20.

To refresh after a patch: read the wiki module again (same way), save a new dated extract, point `WIKI` in the script at it, and re-run.

**Columns**

| Column | Meaning |
|---|---|
| `name`, `riot_id`, `api_name`, `title` | Champion name as in the Oracle's Elixir file, Riot's numeric id, Data Dragon id, title |
| `class`, `class_secondary`, `subclasses` | Riot's class system: archetype (Fighter, Mage, Tank, Marksman, Assassin, Support), secondary archetype, subtypes (e.g. Juggernaut, Burst, Vanguard, Enchanter, Catcher; several joined with `/`) |
| `damage_types` | Physical, Magic or Physical+Magic (Riot's client damage tag; Mixed = both). 3 champions with no tag use Riot's adaptive type (`damage_type_source` says which). True damage is not in the source |
| `damage_tag`, `adaptive_type` | The raw client damage tag; the adaptive stat type Riot sets |
| `riot_damage`, `riot_toughness`, `riot_cc`, `riot_mobility`, `riot_utility` | Riot's own 1–3 style ratings from the client (0 where Riot gives 0). Damage = carry weight, cc = crowd control weight, utility = utility weight |
| `style` | 0 = all basic attacks, 100 = all abilities |
| `playstyle_tags` | Riot's client tags without the damage tag (e.g. Hypercarry, Initiator, Ally Protection) |
| `range_type`, `attack_range`, `resource`, `difficulty` | Melee or Ranged, base attack range, resource, Riot difficulty 1–3 |
| `riot_lane_roles`, `wiki_lane_roles` | Lanes Riot recommends in the client; the wiki's wider list (top, jng, mid, bot, sup) |
| `meta_role`, `meta_role_name`, `meta_role_source`, `meta_role_share` | Dominant pro role: most-played at Worlds if 5+ Worlds games, else across 2026 majors if 5+, else Riot's first lane. The source column says which; the share is that role's share of the sample |
| `off_roles` | Other roles with 10%+ of the champion's games and 2+ games, at Worlds or across 2026 majors |
| `pro_games_2026`, `pro_winrate_2026`, `worlds_games`, `worlds_bans`, `worlds_presence` | Pro games and win rate in 2026 majors; Worlds games, bans and presence ((games + bans) / 94) |
| `pro_dmg_share_meta_role`, `pro_dmg_index_meta_role` | Average share of team damage in its meta role in 2026 majors, and that over the role's average (1.0 = average for the role) |
| `share_2026_<role>`, `share_worlds_<role>` | Share of the champion's games in each role (top, jng, mid, bot, sup) |
| `released`, `last_changed` | Release date; last patch the wiki lists a change |
