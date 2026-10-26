# Aion2Meter · 1.0.0

**English** | [Deutsch](README.de.md)

A Windows live DPS/healing meter for AION 2. English and German UI.


## New in 1.0

[All changes](CHANGELOG.md) · [Deutsch](CHANGELOG.de.md)

UTC resets and regional event times are separate: daily/weekly resets stay at
07:00 UTC (Berlin: 08:00 CET / 09:00 CEST). In **Clock settings → Events**, each
event can override its time zone; an empty field inherits the schedule zone.
Other regional events are not shifted merely because the daily reset moved.

To update, close the old meter, extract this ZIP into a new folder and start
there. Existing LocalAppData settings and logs are retained. Run
`Setup-Meter.cmd` first if dependencies are missing.


## Updates

Use **Updates → Check for updates** in the main window. The meter contacts only
the public releases of `Evilx94/Aion2DPSMeter` when you request a check. Beta
releases can be included or excluded; older published versions are not offered
as a downgrade. No login, automatic startup check or upload of logs/settings.

When a newer matching package is available, **Download and verify** checks its
SHA-256 (GitHub asset digest or attached `.zip.sha256`), file manifest and ZIP
paths, then prepares it under LocalAppData/Aion2Meter/updates. A checksum does
not replace trust in the repository/release owner. Missing or invalid checksums
disable the integrated download; the GitHub release page remains accessible.

**Open prepared update** opens the verified folder. Close the meter before
switching to the new source folder; run Setup-Meter.cmd there if needed and
keep the old folder as a backup. Current program files, settings, logs and
Python are not automatically replaced. Automatic application replacement is not included in 1.0; the update screen
provides manual checking and verified package preparation.

## Features

Movable and resizable overlays; damage/healing and skill details; casts,
observed buff uptime, DoTs and summon attribution; dungeon boss/trash history;
fight comparison; clipboard exports; local logs and data-quality diagnostics;
event clock with fixed schedules and simultaneous events; pet checklist.

## Installation (Windows)

This ZIP is the Python source edition. A separate Windows ZIP contains Aion2Meter.exe and its runtime. Setup is
needed once; subsequent starts use `Start-Meter.cmd`. The meter does not install
anything at startup. Run `Setup-Meter.cmd` explicitly to set up its packages. Keep the complete extracted folder together.

### 1. Download and extract the meter

On GitHub, select **Code > Download ZIP**, then right-click the downloaded ZIP
and choose **Extract All**. Open the extracted folder containing
`Start-Meter.cmd`, `requirements.txt` and the `meter` folder. Do not run it from
inside the ZIP. An attached release ZIP can be extracted in the same way.

### 2. Install Python 3.15 (64-bit)

Download Python only from [python.org](https://www.python.org/downloads/windows/).
Choose **Python 3.15 > Windows installer (64-bit)** for a regular Intel/AMD PC;
do not choose the embeddable package. In the installer, enable the launcher
and **Add Python to PATH** when offered, then complete the installation.
An existing 64-bit Python 3.15 installation can be reused.

Open a new terminal and check:

```powershell
py -3.15 --version
```

It should print `Python 3.15...`. If you use the newer Python Install Manager
instead, install the 3.15 runtime through that manager before continuing.
See the [official Windows setup guide](https://docs.python.org/3.15/using/windows.html).

### 3. Install Npcap

[Npcap](https://npcap.com/#download) is the Windows packet-capture driver used
by Scapy to read the game's network traffic. Install it from its official site;
the driver installer needs Windows administrator approval. A working existing
Npcap installation can be reused. Nmap and Wireshark are not required.

For a fresh setup, leave **WinPcap API-compatible Mode** off, as recommended
by [Scapy's Windows guide](https://scapy.readthedocs.io/en/latest/installation.html#windows).
Raw 802.11/monitor-mode support is not needed for this meter. If capture access
is restricted to administrators, you may need an elevation prompt or to start
`Start-Meter.cmd` using **Run as administrator**. Restart Windows if requested.

Npcap is downloaded separately and retains its own
[license and installation terms](https://npcap.com/guide/npcap-users-guide.html).
No Npcap installer or driver is bundled with this project.

### 4. Run the setup assistant once

Double-click **Setup-Meter.cmd** in the extracted folder. It checks for an
existing 64-bit Python 3.15 installation, creates a local `.venv` environment
and installs the pinned Scapy and PySide6 packages from `requirements.txt`.
Internet access is required for the package downloads. It reports missing
Python or Npcap with official download links; it does not install either of
them, change system settings or start the meter automatically.

The setup window stays open so errors can be read. Run it again if package
installation was interrupted. If Npcap is missing, Python packages can still
be installed, but live capture remains unavailable until Npcap is installed.
Driver detection is only a prerequisite check, not a live-capture test.

**Manual alternative:** open PowerShell in the meter folder and run:

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

No environment activation is needed. Do not upload `.venv` to GitHub.
For a read-only prerequisite check, use
`powershell -NoProfile -File .\Setup-Meter.ps1 -CheckOnly`.

### 5. Start and use the meter

Double-click **Start-Meter.cmd**. Start before logging into AION 2 or joining
a party where possible, so identity and membership messages can be observed.
The meter selects the capture interface automatically. Open **Overlays** to
show DPS, graph or clock; **Settings** contains appearance and behavior options.
Choose English/Deutsch under **Global** and restart to apply the language.

Use **Copy chat text** for the selected fight or **Copy dungeon** for the run,
then paste into chat manually. Nothing is sent to other players automatically.
Event schedules are editable and default to Europe/Berlin (CET/CEST).

### Troubleshooting

| Problem | What to check |
|---|---|
| `py` is not recognized / Python 3.15 is missing | Reopen the terminal after installation. Check the launcher or Python Install Manager and run `py -3.15 --version`. |
| `No module named scapy` or `PySide6` | Repeat step 4 in the extracted folder. Use its `.venv\Scripts\python.exe` so packages go into the correct environment. |
| The app closes or nothing appears | Open PowerShell in the meter folder and run `.\.venv\Scripts\python.exe -m meter` to see the error. |
| Capture is unavailable / access denied | Check Npcap installation and any requested restart or administrator access. See the [Npcap user guide](https://npcap.com/guide/npcap-users-guide.html). |
| Only your character is listed | A fresh member list and live player identities are both needed. Names may already be known while entity IDs are still missing. A group/area transition can supply new records; restarting during a fight may show only self or some members. |
| An attached overlay disappears outside AION 2 | Expected behavior: disable attachment in Settings to keep that overlay free-floating. |

Preferences, combat logs and optional recordings are stored under
`%LOCALAPPDATA%\Aion2Meter`, separately from the source folder. Log saving is
configurable under **Settings > Logs**. For an isolated test, set
`AION2_METER_DATA_DIR` to a fresh folder before starting.

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

## Known limits

World and Abyss bosses show only your own observed damage/DPS, including
attributed pets and periodic damage. Other players' direct amounts are not
reliably available there, so no party/raid ranking or damage-share percentage
is shown. Dungeon and ordinary group combat retain party evaluation.
The recorded encounter duration remains the DPS denominator. Historical
aggregate curves are hidden when no separate personal timeline is available.
Late-start party recognition can still be incomplete.
During late starts, observed unidentified damage sources can appear in the
dungeon/PvE bars as `Sorcerer · Entity 1234 · ?`, with their observed damage/DPS.
The `?` marks unconfirmed group membership. These rows do not change confirmed
group totals, the group graph or chat exports; percentage shares are hidden
while such rows are displayed. Exact later identity evidence replaces the
class placeholder with the name. Same-class players remain separate entities.

Capture gaps and partial encounters are flagged. Some skill variants, buffs
and maps remain unnamed; numerical derivations are not exact confirmations.
Buff uptime starts at observed lifecycle messages. Casts can include automatic
server triggers. TCP latency and capture gaps are not a reliable Internet
packet-loss percentage. Missing damage is not invented.

The public package contains no tests, catalog-analysis tools, private captures,
developer configuration or third-party installer binaries. The setup assistant
only downloads Python packages when explicitly run. Logs are not uploaded automatically.


## Overlay settings

**Settings > Clock** opens the event clock settings. **Attach to AION 2** makes
an overlay follow the game and hide when the game is inactive, minimized or
closed. The DPS/graph attachment selector applies the same behavior to either
or both overlays. The clock has its own attachment and opacity controls.
Free-floating overlays remain independent of the main meter window.

If started in an existing party, the meter waits for a fresh server membership
message. A group or area transition can trigger one. Missing earlier membership
is not reconstructed from nearby damage or an older party list.


## Main application

The main view reports how many roster members have a current live entity
assignment and lists pending names. A received five-name roster is distinct
from five players with assigned identities. The count does not certify that
all their damage packets were captured.


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

Dungeon wipes and player exchanges have been reported successful in repeated
live use. Late start remains limited: a received member-name list alone does
not map every name to a live entity ID, and a mid-fight restart can still count
only self or part of the group. The 22 October update supports additional
structured party snapshots; it does not claim to solve that missing mapping.


When no full member list was captured, repeated validated party-status messages
can recover a **partial** group once matching full player identity records
arrive. Explicit membership/leave records take priority. This does not recover
earlier missed damage or players whose live identity never arrives; a boss-start
capture can still be self-only until those records are sent.


A bounded late-identity buffer can add previously received damage to an open
or retained fight when a later full player record proves the exact identity.
It requires an explicit trusted roster at hit time and unchanged entity
lifecycles. The buffer is limited to 10,000 events and ten minutes; it does not
recover pre-fight hits, missing packets or identities that never arrive.
Partial-status recovery alone does not enable this historical reconciliation.
Reconciled reports remain marked partial. Restart the meter to load updates.


Unassigned attackers at an already observed fight target can appear separately
in the main window as **Player ? · Entity ID**, with observed damage/healing.
Names update when matching identity metadata arrives. These observations are
excluded from confirmed group totals, shares and chat exports until the exact
group proof permits a transfer. The collector is bounded to 20,000 events;
known NPCs/summons and unrelated targets are excluded. The overlay ranking
continues to show confirmed members. A heal alone does not establish membership.


The local periodic policy includes the full credited exact DoT table. Two-value
periodic healing uses the validated first amount; the second field is not added.
Already-active buff lists in player/self/spawn records are also observed. Uptime
starts at observation and timed effects require a server-clock anchor. Missing
exact effect names and unsupported records remain explicitly unresolved.

## License and signing

Project code: [GPL-3.0-only](LICENSE). Third-party notices and game-data
attributions remain in [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md).

[Code signing policy](docs/CODE-SIGNING.md) · [Signing setup (German)](docs/SIGNING.de.md).
Signing is pending SignPath approval; existing local Windows packages are unsigned.
