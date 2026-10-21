# Aion2Meter · 0.1.0 Beta

A Windows live DPS/healing meter for AION 2. English and German UI.

## Features

Movable and resizable overlays; damage/healing and skill details; casts,
observed buff uptime, DoTs and summon attribution; dungeon boss/trash history;
fight comparison; clipboard exports; local logs and data-quality diagnostics;
event clock with fixed schedules and simultaneous events; pet checklist.

## Installation (Windows)

This beta is a Python source package, not a standalone executable. Setup is
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
| Only your character is listed | The meter may still be waiting for a fresh party/raid update. A party or area transition can supply one; earlier membership cannot always be recovered. |
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
