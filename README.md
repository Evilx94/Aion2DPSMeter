# Aion2Meter · 0.1.0 Beta

A Windows live DPS/healing meter for AION 2. English and German UI.

## Features

Movable and resizable overlays; damage/healing and skill details; casts,
observed buff uptime, DoTs and summon attribution; dungeon boss/trash history;
fight comparison; clipboard exports; local logs and data-quality diagnostics;
event clock with fixed schedules and simultaneous events; pet checklist.

## Start

This is a Python source package, not a standalone executable. It needs an
existing Python 3.15 environment with the packages in `requirements.txt` and
an existing Npcap installation. Nothing is installed automatically.

```powershell
python -m pip install -r requirements.txt
python -m meter
```

Use the executable belonging to your Python environment. `Start-Meter.cmd`
supports a local `.venv` or the Windows `py` launcher selecting Python 3.15.
Start before logging in or joining a party so membership can be observed.
Enable overlays in the main window. Select English/Deutsch in Settings and
restart to apply. Event schedules are editable and use Europe/Berlin (CET/CEST).

Preferences, combat logs and optional recordings are stored separately under
`%LOCALAPPDATA%/Aion2Meter`. For an isolated test set `AION2_METER_DATA_DIR`
to a fresh folder. Copy buttons use the clipboard; paste into game chat manually.

## Catalogs and credits

Five local operational catalogs ship under `meter/data`; the other JSON files
are the pet checklist and UI translations. No outside meter, private reference
folder or Internet access is needed to resolve the supplied names.

The catalogs build on credited open-source data and boss sources. We checked,
corrected and extended them with our own recordings, findings and evidenced
mappings. Detailed research and tests remain in the developer edition.
See [catalogs](docs/CATALOG.md), [provenance](docs/PROVENANCE.md),
[third-party notices](THIRD-PARTY-NOTICES.md) and [license status](LICENSE-STATUS.md).
Original reference notices and license text are under `licenses`.

## Beta limits

Worldboss/Open World and late-start party recognition can be incomplete.
Capture gaps and partial encounters are flagged. Some skill variants, buffs
and maps remain unnamed; numerical derivations are not exact confirmations.
Buff uptime starts at observed lifecycle messages. Casts can include automatic
server triggers. TCP latency and capture gaps are not a reliable Internet
packet-loss percentage. Missing damage is not invented.

The public package contains no tests, catalog-analysis tools, private captures,
developer configuration or dependency installers. Nothing is uploaded automatically.


## Overlay settings

**Clock settings** opens the event clock settings. **Attach to AION 2** makes
an overlay follow the game and hide when the game is inactive, minimized or
closed. The DPS/graph attachment selector applies the same behavior to either
or both overlays. The clock has its own attachment and opacity controls.
Free-floating overlays remain independent of the main meter window.

If started in an existing party, the meter waits for a fresh server membership
message. A group or area transition can trigger one. Missing earlier membership
is not reconstructed from nearby damage or an older party list.


## Main application

**Live** focuses on the current encounter, damage/healing filters, encounter
history and sharing. **Overlays** groups visibility, customization and position
locking. **Tools** contains saved logs, storage folders, diagnostics and pets.
Capture status and pause/resume remain available above the tabs. Settings opens
the shared configuration window. All actions remain reachable by scrolling at
small window sizes; your saved window size is preserved.

## Appearance and time zones

All gear buttons open one **Settings** window with **Global**, **DPS / healing**,
**Graph**, **Clock** and **Logs** tabs. Overlay gears select their matching section.
DPS, Graph and Clock have separate **Settings** and **Design** pages; Clock also
has **Events**. Each overlay has independent opacity, colors and typography.
Click **Text color (all)** to change a section's text together, or use individual
text-color swatches. **Other colors** contains backgrounds and other elements.
The live preview shows changes before OK; Cancel discards them. Position, size,
attachment and locking are grouped under the relevant overlay's Settings page.
Changes apply after OK and are saved locally.

Choose **High contrast** for a black/white starting point, or use **Accessible
colors** in the palette selector. This palette keeps each class color stable
when rankings change. Names and class labels remain visible, so color is not the
only identifier. Custom class colors apply with the **Class colors** palette;
**Single color** uses the accent color. The preview shows a contrast ratio;
check your chosen colors in the game too, especially with reduced opacity.

The **Clock** section has **Settings**, **Design** and **Events** tabs. Clock colors,
font, text size and opacity are independent of DPS/graph appearance. The timezone
selectors are searchable and offer all zones available in Qt (489 on the tested
Windows installation), UTC and the system timezone. No additional timezone package
or font installation is performed.

**Clock time zone** changes only the displayed clock. **Event schedule time zone**
interprets the editable event hours and weekdays. Both default to Europe/Berlin
for existing setups. For example, show America/New_York while keeping the current
EU schedule in Europe/Berlin: event instants and countdowns stay unchanged. Choose
a different schedule zone only when those editable hours should use that zone;
this does not download or infer a different region's event calendar. Regional
zones use Qt's daylight-saving rules automatically; UTC stays fixed.

The post-patch party/raid live test is still outstanding. Appearance/timezone
checks do not establish compatibility with a new game protocol patch.
