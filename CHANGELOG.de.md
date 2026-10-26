# Änderungen

[English](CHANGELOG.md) | Deutsch

## 1.0.0 · 26.10.2026

### Portable Windows-Version
- Ein separates Windows-ZIP enthält Aion2Meter.exe, Python und Bibliotheken. Für diese Ausgabe ist keine Python-Installation nötig; Npcap bleibt separat. Der komplette Ordner muss zusammenbleiben. Quellcode und Laufzeit-Lizenzhinweise bleiben verfügbar.
- Vor Veröffentlichung ist ein Laufzeittest nötig; Windows App Control kann unsignierte Builds blockieren.

### Update-Prüfung
- Manuelle GitHub-Release-Prüfung, wählbarer Beta-Kanal, Versionsvergleich und geprüfte Paketvorbereitung. SHA-256, ZIP-Pfade und Dateimanifest werden vor dem Entpacken geprüft. Keine automatische Installation und keine Änderungen an Einstellungen/Logs; automatischer Austausch einer laufenden Installation ist noch nicht enthalten.

### Uhr und Zeitzonen
- Daily- und Weekly-Reset nutzen 07:00 UTC unabhängig von Anzeige- und regionaler Event-Zeitzone. In Berlin liegt der Daily Reset damit um 08:00 CET beziehungsweise 09:00 CEST.
- Jeder Event kann eine eigene Zeitzone erhalten. Bestehende regionale Eventzeiten bleiben in ihrer eingestellten Zone; ein verschobener Reset belegt keine Verschiebung aller Events.
- Fehlende Reset-Einträge werden bei bestehenden Standardplänen einmalig ergänzt. Eigene Pläne, bearbeitete Einträge, deaktivierte Events und bewusste Löschungen bleiben erhalten.
- Zeitumstellung der lokalen Uhr, Countdowns und gleichzeitige Events bleiben unterstützt. Feste Abyss-/Siege-Termine bleiben enthalten; unregelmäßige Worldboss-Spawns bleiben ausgeschlossen.

### Kämpfe und Late Start
- Dungeon-/PvE-Balken können beobachteten, nicht zugeordneten Schaden als Klasse + Entity-ID + `?` mit erfasstem Schaden und DPS anzeigen.
- Das Fragezeichen steht für unbestätigte Gruppenzugehörigkeit. Die Klasse allein ordnet keinen Namen zu, führt keine Spieler zusammen und bestätigt keine Mitgliedschaft. Spätere eindeutige Identitätsdaten können den Namen ergänzen.
- Vorläufige Zeilen bleiben außerhalb bestätigter Gruppensummen, Gruppengraph und Chat-Anteile. Prozentanteile werden in der gemischten Balkenansicht ausgeblendet. Boss-/Trash-Filter nutzen beobachtete Schadensmengen pro Ziel.
- Eine begrenzte Zwischenspeicherung kann geeignete Treffer nachtragen, wenn später eindeutige aktuelle Identitätsdaten und Mitgliedschaftsbelege zum Trefferzeitpunkt vorliegen. Fehlende Pakete oder Identitätsverbindungen werden nicht erfunden.
- Weitere aufgezeichnete Gruppen-/Statusvarianten und Lebenszyklusbehandlung verbessern Teilgruppen, Dungeon-Wiedereintritt und Leave/Rejoin. Normale Wipes und Spielerwechsel funktionierten in Nutzertests; dies ist keine allgemeine Vollständigkeitsgarantie.

### World- und Abyss-Bosse
- Zeigen nur eigenen beobachteten Schaden/DPS, DoTs und zugeordnete Begleiter. Die unvollständige Raidrangliste und irreführende Spieleranteile entfallen bei diesen Bossen.
- Dungeon- und normale Gruppenauswertung bleiben aktiv. Paketkonflikte und Erfassungslücken bleiben sichtbar.

### Aufzeichnung und Analyse
- Ein begrenzter Aufnahmepuffer verlagert Speicherung/Dekodierung aus dem Paket-Callback, erhält die Reihenfolge und kennzeichnet Überläufe ausdrücklich.
- Treffermeldungen ohne Schadensbetrag bleiben separate Aktivitätsbelege; sie erzeugen weder Schaden noch zusätzliche gezählte Schadenstreffer.
- Heilungsansichten, Datenqualität pro Spieler, Log-Verwaltung, Overlays, englische/deutsche Oberfläche und Quellen-/Lizenzhinweise bleiben enthalten.

### Aktualisierung
Vorheriges Meter schließen. Dieses Release in einen neuen Ordner entpacken, bei noch fehlenden Abhängigkeiten `Setup-Meter.cmd` ausführen und anschließend `Start-Meter.cmd` verwenden.
Einstellungen und Logs bleiben am bisherigen Ort unter LocalAppData. Alte Aufnahmen behalten; die Aktualisierung schreibt keine historischen Kampf-Logs oder PCAPs um. Interpreter, Npcap-Installer und Bibliotheks-Binärdateien sind nicht enthalten.

### Bekannte Grenzen
Sofortige Late-Start-Namen benötigen weiterhin eine vom Server gesendete Verbindung zwischen Entity-ID und Name. Nicht zugeordnete Quellen sind Beobachtungen und keine bestätigten Gruppenmitglieder. Vollständige Erfassung ist nicht garantiert; einige Skill-/Statuseffekt-IDs bleiben unbenannt. Alte Gruppenkurven lassen sich nicht nachträglich in eigene Kurven zerlegen. Eventpläne sind bearbeitbare Community-Zeitpläne und keine Live-Erkennung des Serverzustands; UTC-Reset und regionale Ortszeiten sind getrennte Regeln.
