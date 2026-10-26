# Third-party sources and notices

## Local game-data catalogs

The catalogs are based partly on A2Tools/AionMeter, the additional open-source
projects and MetaBot boss sources credited below. They have been checked
against our own recordings, corrected and extended with own findings and
evidenced mappings. Originally sourced entries can also have independent own
confirmations. Existing source and license notices are retained.

The project ships local skill, buff, NPC and location catalogs and exact
periodic-effect classifications under `meter/data`. Runtime files contain only the mappings needed by the meter. Full source
history, original hashes, own observations and explicit confirmations are
preserved in the developer edition under `development/catalogs`. Existing
own entries take precedence.
These tables are not claimed to have been independently extracted in full.
See [catalog structure](docs/CATALOG.md) and [provenance](docs/PROVENANCE.md).

The historical text in `licenses/REFERENCE-NOTICE.md` is preserved in full
after an explicit scope clarification. `REFERENCE-LICENSE.txt` is unchanged.
The historical notice describes upstream paths and assets and earlier
comparison work. No upstream class PNGs or boss portraits were imported or
bundled, and this Python meter does not download boss portraits. Its current
UI displays class names as text and draws action icons in code.

## Source projects

- [cyberbadger6969/aion2-dps-meter](https://github.com/cyberbadger6969/aion2-dps-meter):
  the AionMeter reference; its `data/NOTICE.md` identifies AION 2 game data
  (NCSOFT) and GPL-3.0 sources. The original notice and license are included.
- [taengu/A2Tools-DPS-Meter](https://github.com/taengu/A2Tools-DPS-Meter):
  GPL-3.0; catalog and protocol comparison source.
- [nousx/aion2-dps-meter](https://github.com/nousx/aion2-dps-meter):
  additional exact skill labels; individual source details remain in entries.
- [MetaBot.GG boss list](https://metabot.gg/en/aion-2/bosses):
  source used for boss-name/location comparisons.

## Skill names

The skill catalog includes AionMeter `data/skills/en.json`, itself crediting
A2Tools `src/data`. Additional exact labels came from taengu/A2Tools-DPS-Meter
commit `c9cf6551e8d8c16ed2f547d8aada0d9f016becf9` and nousx/aion2-dps-meter
commit `0d1e0a00a2408cc7b2edd2ce903b0a52193864d0`.

The nousx additions include nine exact Draupnir-observed labels and ID
`17730002`, Empyrean Lord's Grace (Prayer of Amplification), from
`src/main/resources/i18n/skills/en.json`. Their URLs and SHA-256 evidence are
preserved in the developer evidence records. These imported names are not marked as independent own name proofs.

## Monsters and locations

NPC names and boss flags include valid records from AionMeter
`data/npcs/en.json`; invalid placeholders were excluded during import.
Map names include reference-table labels. Boss/location associations were
compared against MetaBot.GG and reference NPC names, including field bosses.
Sources and inference details remain in the developer evidence records.

## Buffs and periodic effects

Buff lifecycle wire layouts were compared against taengu/A2Tools-DPS-Meter
commit `c9cf6551`, `src-tauri/src/capture/abnormal.rs`, which credits
Seralth/Daevalog (GPL-3.0). Exact buff names and stack limits include
`src/data/i18n/abnormals/en.json` and `src/data/abnormals.json`.

Five periodic classifications include facts from AionMeter
`data/dot_skill_ids.json`, whose notice credits taengu/A2Tools-DPS-Meter
commit `e32dc5e` (GPL-3.0). Their individual hashes and provenance remain
in the developer evidence records. The runtime table also includes twenty
own HP-balance-backed classifications. The non-damage interpretation of `0x08` also used AionMeter
`ProtocolTests.cs` (GPL-3.0) and bounded own Draupnir packet examples.

## Worldboss coverage warning

The warning for many periodic-only damage actors with few direct hits follows
`MostDamageUnsent` in AionMeter
`src/AionMeter.Core/Combat/Snapshots.cs` (GPL-3.0). A further warning condition
uses own worldboss observations. Social-login decoders use own observed
packets. These credits remain applicable after catalog consolidation.

## Runtime dependencies and assets

- Python 3.15: Python Software Foundation License and its included notices.
- Scapy 2.8.0: GPL-2.0-only according to the development environment's installed
  package metadata.
- PySide6 6.12.0: LGPL/GPL/commercial licensing options, depending on usage and
  modules.
- Npcap: vendor terms; used from the user's existing installation.

This source package contains no interpreter, Qt/Scapy library binary, Npcap
installer, external meter binary or official game-image asset. Unused
project-created class SVGs are omitted. Classes are displayed as text; action
buttons are drawn in code. Optional user skill images can be loaded from the
runtime directory. Dependencies retain their own terms.

Keeping attribution and checking or extending data does not itself settle the
final project license. See [license status](LICENSE-STATUS.md).

## Pet checklist facts

The 35 shop/chest pet entries were cross-checked against the chest/merchant
section of [Th3Ruthless's AION 2 Pet Farming Guide](https://t3r-aion2-petfarming.netlify.app/),
accessed 2026-10-20. The guide credits [AION 2 Global Database](https://aion2.gaming.tools/)
for monster-to-pet records and [Pet Soul Atlas](https://petsouls.dev/) for
recorded spawns. The previously supplied five dungeon pets and nine special
pets are retained. Ordinary open-world/Abyss farming pets are not included.

The imported facts are pet IDs, names, families and chest/merchant acquisition
categories. The guide's complete pet list, guide prose, artwork, maps, routes
and application code are not part of the meter. Listed shop/chest availability
does not by itself prove exclusive availability. Source evidence is retained
separately in the developer edition under `development/pets`.


Exact periodic classification update, 22 October 2026: IDs 17070120, 17070140 and
17080020 are also listed in the credited AionMeter reference's
`data/dot_skill_ids.json`. These entries were missing from our local periodic
policy despite existing skill labels. Own structured capture observations
corroborate their occurrence. Existing source/license notices remain applicable;
no neighboring-ID classification was inferred.


Recurring-effect correction, 22 October 2026: the complete exact
`data/dot_skill_ids.json` table (2,641 IDs) from the credited AionMeter reference
is consolidated in the local periodic catalog. Existing own classifications
remain. Periodic two-value healing follows that reference's
`PacketParser.ParseDot` first-amount handling; the second field stays opaque.
Buff lists embedded in player/self/spawn records use a bounded Python port of
A2Tools `abnormal.rs` listed/listed_entry, already credited above to
Seralth/Daevalog. Existing GPL/source notices remain applicable. No game images
or external binaries are added.


Party/raid leave correction, 23 October 2026: exact 13 92 / 1d 97 leave
envelopes follow the already credited A2Tools stream_processor.rs
parse_party_left_packet (cf222411ee57b82b633c1dd9b9c7b88b646159e8).
Existing GPL/source notices remain applicable. Additional 2b96/2c96 raid
status validation and subgroup-resnapshot diagnostics use this project's
own captures; no additional external game-data table or binary is bundled.

The landed-hit notice parser (`meter/core/hit_notice.py`, opcode `03 38`)
uses the documented layout from the credited AionMeter reference's
`src/AionMeter.Core/Protocol/PacketParser.cs`, `ParseHitNotice` (GPL-3.0).
Our strict full-body validation was checked against the private Nahma capture
on 2026-10-23. These notices provide activity evidence only and are never
converted into damage amounts.


## Separate Windows executable distribution

The source ZIP remains available alongside the Windows package. The portable
Windows package additionally includes the unmodified CPython runtime, Scapy,
PySide6/Qt and Shiboken, and a PyInstaller bootloader. Their terms are retained
under `licenses/runtime`. PyInstaller's bootloader exception is preserved.
Qt libraries remain separate DLLs. Scapy's Python sources are provided under
`third-party-sources/scapy`; the corresponding application source is published
alongside the executable package. Qt/PySide source locations and versions are
listed in the Windows package's `RUNTIME-COMPONENTS.md`.
No Npcap installer, driver, wpcap.dll or Packet.dll is redistributed.
