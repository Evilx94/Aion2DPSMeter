# Scope of this historical reference notice

**The text below describes the reference AionMeter project and earlier
comparison work. It is not a list of assets, file formats or downloads used
by this Python Aion2Meter.**

- No class-emblem PNGs from the referenced meters were imported or bundled.
- No boss portraits are bundled, and this meter does not download portraits
  from MetaBot.GG or other sites.
- The old project-created geometric SVG class markers have also been removed.
  The current UI displays class names as text and draws action icons in code.
- Optional skill images explicitly supplied by a user can be read from that
  user's local runtime folder; these are not supplied by this package.
- Upstream table paths, language fallback, image handling and statements about
  "AionMeter as a whole" below refer to that reference project. Mentions of
  private catalogs describe earlier development stages, not the current
  runtime layout or the final license of this Python project.

Applicable data/protocol sources and our own contributions are summarised in
[THIRD-PARTY-NOTICES.md](../THIRD-PARTY-NOTICES.md).
The historical text is preserved below for source attribution.

---

# Game data tables

The lookup tables in this folder are extracted from AION 2 game data (© NCSOFT) and were taken from
open-source meters licensed under GPL-3.0, which is why AionMeter as a whole is distributed under GPL-3.0
(see `../LICENSE`).

| File | Source |
|---|---|
| `skills/*.json`, `npcs/*.json`, `dungeons/*.json`, `dot_skill_ids.json`, `servers.json`, `skill_icons.json` | [taengu/A2Tools-DPS-Meter](https://github.com/taengu/A2Tools-DPS-Meter) `src/data`, commit `e32dc5e` (2026-10-05), GPL-3.0 |
| `healing_skill_ids.json` | [Kuroukihime/AIon2-Dps-Meter](https://github.com/Kuroukihime/AIon2-Dps-Meter) `GameData/Assets`, commit `2e8d67d` (2026-10-01), GPL-3.0 |
| `src/AionMeter.App/Assets/Classes/*.png` (class emblems; brawler downscaled to 128 px) | same repository, `AionDpsMeter.UI/Assets/Classes`, commit `2e8d67d`, GPL-3.0 |
| `boss_portraits.json` (NPC code → portrait file) | built from [MetaBot.GG's boss list](https://metabot.gg/en/aion-2/bosses) (2026-10-05): each dungeon boss's portrait file, matched to every NPC code with the same English name in `npcs/en.json`. The portraits themselves are not bundled: the app downloads them from MetaBot.GG at runtime (credit: [MetaBot.GG](https://metabot.gg)) |

Formats AionMeter reads (every file is optional):

- `skills/<lang>.json` — `{ "16040000": "Skill name", … }`
- `npcs/<lang>.json` — `{ "2000002": { "name": "…", "isBoss": false, "isDummy": false }, … }`
- `dungeons/<lang>.json` — `{ "600021": { "name": "Fire Temple" }, … }` (map id → name)
- `servers.json` — `{ "servers": { "2305": { "en": "…", "ru": "…" } } }`
- `dot_skill_ids.json`, `healing_skill_ids.json` — arrays of skill codes
- `field_boss_maps.json` — `{ "maps": { "1110": { "block": 2400, "en": "Altgard", "ru": "Альтгард" } } }`: a map's field boss
  list (opcode 01 91) holds its bosses in NPC-code order, all from one block of a thousand codes. Established on the
  2026-10-06 EU capture against the in-game list (24 of 24 slots).
- `boss_portraits.json` — `{ "portraits": { "2300471": "2300471", "2300104": "f/mob_berc_01", … } }` (file name on
  metabot.gg/web/aion2/npcs/ without `.webp`; NPCs not listed are tried under their own code)

Missing languages fall back to `en`.

## Exact skill comparison, 2026-10-13

- https://github.com/taengu/A2Tools-DPS-Meter/blob/c9cf6551e8d8c16ed2f547d8aada0d9f016becf9/src/data/i18n/skills/en.json: exact IDs [1900001]. GPL-3.0 source project; names kept only in the optional private catalog.
- https://github.com/nousx/aion2-dps-meter/blob/0d1e0a00a2408cc7b2edd2ce903b0a52193864d0/src/main/resources/i18n/skills/en.json: exact IDs [15320007, 17730001]. GPL-3.0 source project; names kept only in the optional private catalog.
- Theostone reduced-ID naming is corroborated by https://github.com/taengu/A2Tools-DPS-Meter/blob/c9cf6551e8d8c16ed2f547d8aada0d9f016becf9/public/src/js/i18n.js (getSkillName, ID * 10 + 1). No damage/DoT rule imported.

Seven exact ailment labels added on 2026-10-13: https://raw.githubusercontent.com/taengu/A2Tools-DPS-Meter/c9cf6551e8d8c16ed2f547d8aada0d9f016becf9/src/data/i18n/skills/en.json. IDs 1200010, 1200011, 1200012, 1200014, 1200015, 1200016, 1200018. Existing GPL-3.0 attribution retained; no class assignments or decoder rules derived from these names.

Fire Temple exact-name additions, 2026-10-13: https://raw.githubusercontent.com/nousx/aion2-dps-meter/0d1e0a00a2408cc7b2edd2ce903b0a52193864d0/src/main/resources/i18n/skills/en.json. IDs 11290001, 14720007, 14770007, 14780008, 14800007. These are direct exact-key entries, not names inferred from their base families. Existing source/license notices retained.
