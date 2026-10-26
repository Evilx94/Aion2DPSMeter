# Changes

English | [Deutsch](CHANGELOG.de.md)

## 1.0.0 · 2026-10-26

### Portable Windows package
- A separate onedir Windows ZIP contains Aion2Meter.exe, Python and its libraries. No Python installation is required for that edition; Npcap remains separate. Keep the complete folder together. Source and runtime license notices remain available.
- Runtime execution must be validated before publication; Windows App Control can reject unsigned builds.

### Update checks
- Manual GitHub release checks, beta channel selection, semantic version comparison and verified package staging. SHA-256, ZIP paths and source manifests are validated before extraction. No automatic installation or changes to settings/logs; automatic replacement of a running installation is not included.

### Clock and time zones
- Daily and weekly resets use 07:00 UTC independently of the display or regional event zone. Berlin therefore shows the daily reset at 08:00 CET and 09:00 CEST.
- Each event can override the schedule zone. Existing regional event times remain in their configured zone; a reset moving does not prove that all events move.
- Standard existing plans gain missing reset entries once. Custom plans, edited entries, disabled events and intentional removals are preserved.
- Local clock daylight saving, countdowns and simultaneous-event display remain supported. Fixed Abyss/siege events stay included; irregular field-boss spawns stay excluded.

### Combat and late start
- Dungeon/PvE bars can display observed, unassigned damage as class + Entity ID + `?`, including its observed damage and DPS.
- The question mark means group membership is unconfirmed. Class alone never assigns a roster name, joins players or confirms membership. Later exact identity evidence can supply a name.
- Provisional rows remain outside confirmed group totals, group graph and chat shares. Shares are hidden in the mixed bar view. Boss/trash filters use observed per-target amounts.
- Bounded delayed-hit reconciliation can attach eligible observations after exact current identity and event-time membership evidence arrives. Missing packets or missing identity links are not invented.
- Additional captured group/status variants and lifecycle handling cover partial parties, dungeon re-entry and leave/rejoin cases. User testing found normal wipe/member changes working; this is not a universal completeness guarantee.

### World and Abyss bosses
- Show only the local player's observed damage/DPS, DoTs and attributed pets. Remove the incomplete raid ranking and misleading player shares for these bosses.
- Dungeon and ordinary group evaluation remain enabled. Capture conflicts and missing-data warnings remain visible.

### Capture and analysis
- Bounded capture intake moves recording/decoding work out of the packet callback, preserves processing order and makes overflow explicit.
- Hit notices without an amount remain separate activity evidence; they never create damage amounts or inflate damage hit counts.
- Existing healing views, player quality diagnostics, log management, overlays, English/German UI and source/license notices remain included.

### Update
Close the previous meter before starting this version. Extract this release to a new folder, run `Setup-Meter.cmd` if its dependencies are not already available, then use `Start-Meter.cmd`.
The same LocalAppData settings/log location is retained. Keep old recordings; no migration rewrites historical combat logs or PCAPs. No interpreter, Npcap installer or library binaries are bundled.

### Known limits
Immediate late-start names still require a server-provided Entity-to-name link. Unassigned sources are observations, not confirmed party members. Full capture coverage is not guaranteed; some skill/status-effect IDs remain unnamed. Historical group curves cannot be separated into personal curves after the fact. Event schedules are editable community plans, not live server-state detection; UTC reset times and regional wall-clock events are separate rules.
