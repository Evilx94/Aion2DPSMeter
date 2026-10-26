# Aion2Meter · 1.0.0

[English](README.md) | **Deutsch**

Ein Live-Meter für Schaden und Heilung in AION 2 unter Windows.
Die Oberfläche ist auf Englisch und Deutsch verfügbar.


## Neu in 1.0

[Alle Änderungen](CHANGELOG.de.md) · [English](CHANGELOG.md)

UTC-Resets und regionale Eventzeiten sind getrennt: Daily-/Weekly-Reset bleiben
bei 07:00 UTC (Berlin: 08:00 CET / 09:00 CEST). In **Clock settings → Events**
kann jeder Event eine eigene Zeitzone erhalten; ohne Eintrag gilt die Plan-Zone.
Andere regionale Zeiten werden nicht allein wegen des Daily Resets verschoben.

Zum Aktualisieren das alte Meter schließen, dieses ZIP in einen neuen Ordner
entpacken und dort starten. Einstellungen und Logs unter LocalAppData bleiben
erhalten. Bei fehlenden Abhängigkeiten zuerst `Setup-Meter.cmd` ausführen.


## Updates

Im Hauptfenster **Updates → Nach Updates suchen** öffnen. Erst nach deinem
Klick fragt das Meter die öffentlichen Releases von `Evilx94/Aion2DPSMeter` ab.
Beta-Releases lassen sich ein-/ausschließen; ältere veröffentlichte Versionen
werden nicht als Downgrade angeboten. Kein Login, keine automatische Abfrage
beim Start und kein Upload von Logs oder Einstellungen.

Bei einem neueren passenden Paket prüft **Herunterladen und prüfen** dessen
SHA-256 (GitHub-Asset-Digest oder angehängte `.zip.sha256`), Dateimanifest und
ZIP-Pfade. Anschließend liegt es unter LocalAppData/Aion2Meter/updates bereit.
Eine Prüfsumme ersetzt nicht das Vertrauen in Repository und Herausgeber.
Fehlt die Prüfsumme oder ist sie ungültig, bleibt der integrierte Download
gesperrt; die GitHub-Release-Seite kann weiterhin geöffnet werden.

**Vorbereitetes Update öffnen** öffnet den geprüften Ordner. Vor dem Wechsel
das Meter schließen, im neuen Quellcode-Ordner gegebenenfalls Setup-Meter.cmd
ausführen und den alten Ordner als Backup behalten. Laufendes Programm,
Einstellungen, Logs und Python werden nicht automatisch ersetzt. Der automatische
Programmaustausch ist in 1.0 noch nicht enthalten; die Update-Ansicht bietet
manuelle Prüfung und verifizierte Paketvorbereitung.

## Funktionen

- Verschiebbare und größenverstellbare Overlays mit anpassbaren Farben und Schriftgrößen.
- Schadens- und Heilungsansicht mit Skilldetails und Runenanzeige.
- Casts, beobachtete Buff-Uptime, DoTs und Zuordnung von Begleiterschaden.
- Dungeon-Verlauf mit Boss- und Trash-Auswertung sowie Kampfvergleich.
- Kampf- und Dungeon-Zusammenfassungen zum Kopieren in die Zwischenablage.
- Lokale Logs, Log-Verwaltung, Datenqualitätsanzeige und Diagnoseexport.
- Event-Uhr mit festen Terminen, gleichzeitigen Events und wählbaren Zeitzonen.
- Pet-Checkliste.

## Installation unter Windows

Diese Beta enthält Python-Quellcode und ist keine eigenständige EXE-Datei.
Die Einrichtung ist einmalig nötig; danach genügt `Start-Meter.cmd`.
Beim Start installiert das Meter nichts. Für die Einrichtung seiner Python-Pakete
startest du ausdrücklich `Setup-Meter.cmd`. Lass den entpackten Ordner vollständig zusammen.

### 1. Meter herunterladen und entpacken

Lade das ZIP der gewünschten Version unter **Releases** herunter. Alternativ
kannst du auf der GitHub-Projektseite **Code > Download ZIP** verwenden.
Klicke im Windows-Explorer mit der rechten Maustaste auf das ZIP und wähle
**Alle extrahieren**. Öffne anschließend den entpackten Ordner, in dem
`Setup-Meter.cmd`, `Start-Meter.cmd`, `requirements.txt` und der Ordner `meter` liegen.
Starte die Dateien nicht direkt innerhalb des ZIP-Archivs.

### 2. Python 3.15 in der 64-Bit-Version installieren

Lade Python von der [offiziellen Python-Webseite](https://www.python.org/downloads/windows/).
Für einen normalen Intel-/AMD-PC wählst du bei **Python 3.15** den
**Windows installer (64-bit)**, nicht das „embeddable package“.
Aktiviere im Installationsprogramm den Launcher und **Add Python to PATH**, soweit
angeboten, und schließe die Installation ab. Ein bereits vorhandenes
64-Bit-Python 3.15 kannst du weiterverwenden.

Öffne danach ein neues Terminal und prüfe:

```powershell
py -3.15 --version
```

Die Ausgabe sollte mit `Python 3.15` beginnen. Falls du stattdessen den neueren
Python Install Manager verwendest, installiere darüber zuerst die Laufzeit 3.15.
Weitere Hinweise stehen in der [offiziellen Windows-Anleitung](https://docs.python.org/3.15/using/windows.html).

### 3. Npcap installieren

[Npcap](https://npcap.com/#download) ist der Windows-Treiber, mit dem Scapy den
Netzwerkverkehr des Spiels erfassen kann. Lade den Installer von der offiziellen
Webseite herunter und führe ihn aus. Die Treiberinstallation benötigt eine
Windows-Administratorbestätigung. Eine funktionierende vorhandene Npcap-Installation
kannst du weiterverwenden. Nmap und Wireshark werden nicht benötigt.

Lass bei einer neuen Installation **WinPcap API-compatible Mode** ausgeschaltet,
wie es die [Scapy-Anleitung für Windows](https://scapy.readthedocs.io/en/latest/installation.html#windows)
empfiehlt. Raw-802.11-/Monitor-Modus-Unterstützung wird für das Meter nicht benötigt.
Wenn der Treiberzugriff auf Administratoren beschränkt wurde, kann eine
Berechtigungsabfrage oder **Rechtsklick auf Start-Meter.cmd > Als Administrator ausführen**
nötig sein. Starte Windows neu, falls der Installer dazu auffordert.

Npcap wird separat heruntergeladen und behält seine eigenen
[Lizenz- und Installationsbedingungen](https://npcap.com/guide/npcap-users-guide.html).
Dieses Projekt enthält keinen Npcap-Installer und keine Treiberdateien.

### 4. Setup-Assistenten einmal ausführen

Starte im entpackten Ordner **Setup-Meter.cmd** per Doppelklick.
Der Assistent prüft vorhandenes 64-Bit-Python 3.15, erstellt eine lokale
Python-Umgebung im Unterordner `.venv` und installiert die festgelegten Versionen
von Scapy und PySide6 aus `requirements.txt`. Dafür ist eine Internetverbindung nötig.

Fehlt Python oder Npcap, zeigt der Assistent einen Hinweis mit dem offiziellen
Download-Link. Er installiert weder Python noch Npcap, verändert keine
Systemeinstellungen und startet das Meter nicht automatisch.

Das Setup-Fenster bleibt offen, damit Fehlermeldungen lesbar sind. Wird die
Paketinstallation unterbrochen, kannst du `Setup-Meter.cmd` erneut starten.
Fehlt Npcap, können die Python-Pakete trotzdem eingerichtet werden; die
Live-Erfassung funktioniert erst nach der Npcap-Installation. Die Treibererkennung
im Setup ist eine Vorprüfung und kein Test der tatsächlichen Live-Erfassung.

**Manuelle Alternative:** Öffne im Meter-Ordner PowerShell. Dazu kannst du in
die Adressleiste des Windows-Explorers `powershell` eingeben und Enter drücken.
Führe diese Befehle einzeln aus:

```powershell
py -3.15 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Du musst die Umgebung nicht zusätzlich aktivieren. Lade `.venv` nicht auf GitHub hoch.
Für eine reine Prüfung ohne Einrichtung kannst du folgenden Befehl verwenden:

```powershell
powershell -NoProfile -File .\Setup-Meter.ps1 -CheckOnly
```

### 5. Meter starten und verwenden

Starte **Start-Meter.cmd** per Doppelklick. Starte das Meter möglichst vor dem
Login in AION 2 beziehungsweise vor dem Gruppenbeitritt, damit die Meldungen
zur Charakter- und Gruppenerkennung mitgelesen werden können. Der Netzwerkadapter
wird automatisch ausgewählt.

Unter **Overlays** kannst du DPS, Graph und Uhr einblenden. **Settings / Einstellungen**
öffnet die gemeinsamen Einstellungen. Unter **Global > Language / Sprache**
wählst du Deutsch oder Englisch. Starte das Meter nach einer Sprachänderung neu.

Mit **Chattext kopieren** kopierst du den angezeigten Kampf, mit **Dungeon kopieren**
die Bosskämpfe des Dungeon-Laufs. Füge den Text selbst in den Spielchat ein;
das Meter verschickt keine Chatnachrichten automatisch.
Die Event-Zeiten sind bearbeitbar und verwenden standardmäßig Europe/Berlin (MEZ/MESZ).

### Hilfe bei Startproblemen

| Problem | Lösung bzw. Prüfung |
|---|---|
| `py` wird nicht erkannt oder Python 3.15 fehlt | Nach der Installation ein neues Terminal öffnen. Launcher bzw. Python Install Manager prüfen und `py -3.15 --version` ausführen. |
| `No module named scapy` oder `PySide6` | Schritt 4 wiederholen. Bei manueller Installation `.venv\Scripts\python.exe` aus dem entpackten Meter-Ordner verwenden. |
| Das Fenster schließt sich oder es erscheint nichts | PowerShell im Meter-Ordner öffnen und `.\.venv\Scripts\python.exe -m meter` ausführen, damit der Fehler sichtbar bleibt. |
| Erfassung nicht verfügbar oder Zugriff verweigert | Npcap-Installation, eventuell erforderlichen Neustart und Administratorzugriff prüfen. Siehe [Npcap-Anleitung](https://npcap.com/guide/npcap-users-guide.html). |
| Nur der eigene Charakter erscheint | Mitgliederliste und aktuelle Spieler-Identitäten müssen vorliegen. Namen können bereits bekannt sein, während die Entity-Zuordnung noch fehlt. Gruppen-/Gebietswechsel können neue Meldungen liefern; ein Neustart im Kampf kann weiterhin nur dich oder einzelne Mitglieder erfassen. |
| Ein angeheftetes Overlay verschwindet außerhalb von AION 2 | Das ist vorgesehen. Deaktiviere das Anheften in den Einstellungen, wenn das Overlay frei schwebend sichtbar bleiben soll. |

Einstellungen, Kampflogs und optionale Paketmitschnitte liegen getrennt vom
Programmordner unter `%LOCALAPPDATA%\Aion2Meter`.
Das Speichern konfigurierst du unter **Einstellungen > Logs**.
Für einen getrennten Test kannst du vor dem Start die Umgebungsvariable
`AION2_METER_DATA_DIR` auf einen neuen Ordner setzen.

## Kataloge und Quellen

Unter `meter/data` liegen fünf lokale Kataloge für den laufenden Betrieb.
Die weiteren JSON-Dateien enthalten die Pet-Checkliste und die Oberflächentexte.
Für die mitgelieferten Namen sind kein anderes Meter, kein privater
Referenzordner und kein Internetzugriff zur Namensauflösung erforderlich.

Die Kataloge bauen auf den genannten Open-Source-Daten und Boss-Quellen auf.
Wir haben sie mit eigenen Mitschnitten, Erkenntnissen und belegten Zuordnungen
geprüft, korrigiert und erweitert. Ausführliche Untersuchungen und Tests bleiben
in der Entwicklerversion. Siehe [Kataloge](docs/CATALOG.md),
[Herkunft](docs/PROVENANCE.md), [Drittanbieterhinweise](THIRD-PARTY-NOTICES.md)
und [Lizenzstatus](LICENSE-STATUS.md). Die ursprünglichen Referenzhinweise
und Lizenztexte liegen im Ordner `licenses`.

## Bekannte Einschränkungen

World- und Abyss-Bosse zeigen nur deinen eigenen beobachteten Schaden/DPS,
einschließlich zugeordneter Begleiter und periodischem Schaden. Direkte
Schadensbeträge anderer Spieler stehen dort nicht zuverlässig zur Verfügung;
deshalb gibt es dort keine Gruppen-/Raidrangliste oder Schadensanteile.
Dungeon- und normale Gruppenkämpfe behalten ihre Gruppenauswertung.
Für DPS gilt weiterhin die erfasste Kampfdauer. Alte Gruppenkurven werden
ausgeblendet, wenn keine eigene Zeitreihe vorliegt.
Die Gruppenerkennung bei spätem Start kann weiterhin unvollständig sein.
Beim späten Start können beobachtete, noch nicht zugeordnete Schadensquellen
in der Dungeon-/PvE-Balkenanzeige als `Sorcerer · Entity 1234 · ?` mit ihrem
erfassten Schaden/DPS erscheinen. Das `?` kennzeichnet eine unbestätigte
Gruppenzugehörigkeit. Diese Zeilen verändern weder bestätigte Gruppensummen
noch Gruppengraph oder Chattext; Prozentanteile werden dabei ausgeblendet.
Eine spätere eindeutige Identitätsmeldung ergänzt den Namen. Spieler derselben
Klasse bleiben über ihre Entity-IDs getrennt.

Erfassungslücken und Teilausschnitte werden markiert.
Einige Skillvarianten, Buffs und Karten sind noch unbenannt; eine numerisch
abgeleitete Zuordnung ist keine exakte Einzelbestätigung.

Buff-Uptime beginnt mit den tatsächlich beobachteten Meldungen. Cast-Zählungen
können automatische Server-Auslösungen enthalten. TCP-Latenz und Erfassungslücken
ergeben keine verlässliche Prozentzahl für Internet-Paketverlust.
Fehlender Schaden wird nicht hinzugerechnet.

Das öffentliche Paket enthält keine Tests, Kataloganalyse-Werkzeuge, privaten
Mitschnitte, Entwicklerkonfiguration oder Installer-Binärdateien von Drittanbietern.
Der mitgelieferte Setup-Assistent lädt Python-Pakete nur beim ausdrücklichen
Ausführen herunter. Es werden keine Logs automatisch hochgeladen.

## Haupt-App

Die Hauptansicht zeigt, für wie viele Mitglieder eine aktuelle Entity-Zuordnung
vorliegt, und nennt ausstehende Spieler. Eine Liste mit fünf Namen bedeutet
noch keine Zuordnung aller fünf Spieler. Auch die vollständige Zuordnung
bestätigt nicht, dass sämtliche Schadenspakete erfasst wurden.


- **Live:** aktueller Kampf, Schaden-/Heilungsfilter, Verlauf und Kopierfunktionen.
- **Overlays:** Sichtbarkeit, Design-Anpassung und Fixieren der Positionen.
- **Tools / Werkzeuge:** gespeicherte Logs, Speicherordner, Diagnose und Pets.

Verbindungsstatus sowie Pausieren/Fortsetzen bleiben oberhalb der Reiter erreichbar.
**Settings / Einstellungen** öffnet die gemeinsame Konfiguration.
Bei kleinen Fenstern bleiben die Bedienelemente durch Scrollen erreichbar;
die gespeicherte Fenstergröße bleibt erhalten.

## Overlay-Einstellungen

Die Zahnräder öffnen die gemeinsamen Einstellungen direkt im passenden Bereich.
Mit **An AION 2 anheften** folgt ein Overlay dem Spielfenster und verschwindet,
wenn das Spiel inaktiv, minimiert oder geschlossen ist. Die Auswahl für DPS und
Graph kann eines oder beide Overlays anheften. Die Uhr besitzt eine eigene
Anheftungs- und Deckkrafteinstellung. Frei schwebende Overlays bleiben unabhängig
vom Hauptfenster des Meters sichtbar.

Wird das Meter erst in einer bestehenden Gruppe gestartet, wartet es auf eine
neue Mitgliedermeldung vom Server. Gruppen- oder Gebietswechsel können diese
liefern. Es wird keine Gruppe aus dem Schaden vorbeilaufender Spieler oder aus
veralteten Mitgliederlisten rekonstruiert.

## Darstellung und Zeitzonen

Das Einstellungsfenster enthält **Global**, **DPS / Heilung**, **Graph**, **Uhr**
und **Logs**. DPS, Graph und Uhr haben eigene Unterseiten für **Einstellungen**
und **Design**; bei der Uhr gibt es zusätzlich **Events**.
Jedes Overlay hat eigene Farben, Schrift, Schriftgröße und Deckkraft.

Über **Textfarbe (alle)** änderst du die Textfarben des jeweiligen Bereichs
gemeinsam. Die einzelnen Textfarben lassen sich auch separat einstellen.
**Weitere Farben** enthält unter anderem Hintergründe. Die Vorschau zeigt
Änderungen vor dem Speichern. **OK** übernimmt und speichert sie lokal,
**Abbrechen** verwirft die Änderungen. Größe, Anheften und Fixieren findest du
auf der Einstellungsseite des jeweiligen Overlays.

Die Vorlage **Hoher Kontrast** bietet einen schwarz-weißen Ausgangspunkt.
Die Palette **Barrierearm** hält Klassenfarben auch bei geänderter Rangfolge
stabil. Namen und Klassenbezeichnungen bleiben zusätzlich sichtbar.
Eigene Klassenfarben gelten bei der Palette **Klassenfarben**;
**Einfarbig** verwendet die Akzentfarbe. Die Vorschau zeigt ein Kontrastverhältnis.
Prüfe deine Farben auch im Spiel, insbesondere bei verringerter Deckkraft.

Die Uhr hat eigene Farben, Schriftgröße und Deckkraft. Die Zeitzonenauswahl
ist durchsuchbar und enthält alle von Qt angebotenen Zeitzonen, UTC und die
Systemzeitzone. Auf dem getesteten Windows-System waren 489 Qt-Zonen verfügbar.
Es werden keine zusätzlichen Zeitzonenpakete oder Schriftarten installiert.

Die **Uhr-Zeitzone** ändert nur die angezeigte Uhrzeit. Die **Event-Zeitzone**
bestimmt, wie die eingetragenen Event-Uhrzeiten und Wochentage interpretiert
werden. Beide verwenden anfangs Europe/Berlin. Du kannst beispielsweise die
Uhr in America/New_York anzeigen und die vorhandenen EU-Event-Zeiten weiter
in Europe/Berlin lassen: Die Event-Zeitpunkte und Countdowns ändern sich dadurch nicht.
Eine andere Event-Zeitzone lädt keinen neuen regionalen Event-Kalender.
Regionale Zeitzonen berücksichtigen die Sommerzeit über Qt automatisch;
UTC bleibt unverändert.

Wipes und Spielerwechsel in Dungeons wurden im wiederholten Live-Einsatz als
funktionierend zurückgemeldet. Der späte Start bleibt eingeschränkt: Eine
empfangene Namensliste ordnet noch nicht jeden Namen einer aktuellen Entity-ID zu.
Nach einem Neustart im Kampf können daher weiterhin nur du oder einzelne
Gruppenmitglieder gezählt werden. Die Änderung vom 22. Oktober unterstützt
zusätzliche strukturierte Gruppenmeldungen; die fehlende Zuordnung wird damit
nicht allgemein behoben.


Fehlt die vollständige Mitgliederliste, können wiederholte geprüfte
Gruppenstatusmeldungen eine **teilweise** Wiederherstellung ermöglichen,
sobald passende vollständige Spieler-Identitätsmeldungen eintreffen.
Ausdrückliche Mitglieder- und Austrittsmeldungen haben Vorrang. Früher fehlender
Schaden und Spieler ohne aktuelle Identitätsmeldung werden dadurch nicht
nachträglich ergänzt; ein Start direkt beim Boss kann weiterhin zunächst nur
den eigenen Charakter erfassen.


Ein begrenzter Puffer kann bereits empfangenen Schaden nachträglich einem offenen
oder noch vorgehaltenen Kampf zuordnen, sobald eine vollständige Spielermeldung
die genaue Identität beweist. Dafür muss beim Treffer eine ausdrückliche geprüfte
Gruppenliste vorliegen; die Entity-Zuordnung darf sich nicht geändert haben.
Die Grenze liegt bei 10.000 Ereignissen und zehn Minuten. Treffer vor Kampfbeginn,
fehlende Pakete und nie eintreffende Identitäten werden nicht rekonstruiert.
Die teilweise Wiederherstellung allein über Statusmeldungen reicht dafür nicht.
Ergänzte Berichte bleiben als unvollständig markiert. Änderungen erfordern einen
Neustart des Meters.


Nicht zugeordnete Angreifer an einem bereits erfassten Kampfziel erscheinen im
Hauptfenster separat als **Spieler ? · Entity-ID**, mit beobachtetem Schaden und
Heilung. Passende Identitätsmeldungen ergänzen später den Namen. Bis ein genauer
Gruppenbeleg die Übernahme erlaubt, bleiben diese Werte außerhalb der bestätigten
Gruppensumme, Prozentanteile und Chat-Exporte. Die Sammlung ist auf 20.000
Ereignisse begrenzt; bekannte NPCs/Begleiter und fremde Kampfziele sind ausgeschlossen.
Die Overlay-Rangliste zeigt weiterhin bestätigte Mitglieder. Eine Heilung allein
belegt keine Gruppenzugehörigkeit.


Die lokale Klassifikation enthält die vollständige berücksichtigte Tabelle
exakter DoT-IDs. Periodische Heilung mit zwei Zahlenfeldern verwendet die erste
geprüfte Menge; das zweite Feld wird nicht addiert. Bereits aktive Bufflisten
in Spieler-, Eigen- und Spawnmeldungen werden ebenfalls erfasst. Uptime beginnt
bei der Beobachtung; zeitlich begrenzte Effekte benötigen eine Zeitbasis.
Fehlende genaue Effektnamen und unbestätigte Formate bleiben ausdrücklich offen.

## Lizenz und Signierung

Projektcode: [GPL-3.0-only](LICENSE). Drittanbieter- und Spieldatenhinweise
bleiben in [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md) erhalten.

[Code signing policy](docs/CODE-SIGNING.md) · [Signierung einrichten](docs/SIGNING.de.md).
SignPath-Freigabe und Signierung stehen noch aus; vorhandene lokale Windows-Pakete sind unsigniert.
