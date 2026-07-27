# Sicherheit (safety.md)

## Elektrische Sicherheit (230 V)

- Arbeiten an 230 V **nur fachgerecht** durch eine Elektrofachkraft.
- FI/RCD + Leitungsschutzschalter, **eigene Sicherung je Lastgruppe**.
- **PE niemals schalten.** Berührungsschutz, Zugentlastung, Leitungen
  ausreichend dimensioniert.
- **Keine 230-V-Leitung direkt am KC868-A16.** Netzlasten ausschließlich über
  Koppelrelais/Schütze (KC868 schaltet nur die 12-V-Spule).
- Freilaufdiode bei DC-Spulen (Ventile/Pumpe/Relais), falls nicht integriert.
- Kleinspannung (SELV) und Netzspannung getrennt führen; gemeinsame Masse nur,
  wo elektrisch vorgesehen; galvanische Trennung prüfen.
- Feuchte Umgebung: geeignete Schutzart, Kondensat fern von Elektronik.
- **Not-Aus** trennt die gefährlichen Lasten **hardwareseitig** (Schütz), nicht
  nur per Software.

## Sichere Bootzustände KC868-A16

Beim Start: alle Ventile AUS, Pumpe AUS, LED AUS, Abluft konfigurierbar
(Default **EIN** als thermischer Failsafe). Keine Wiederherstellung gefährlicher
Ausgänge. **Niemals** `restore_mode: ALWAYS_ON` für Pumpe/Ventile/LED.

## Watchdog / Heartbeat (Modbus)

Bleibt der Master-Heartbeat (0x0004) länger als `watchdog_time_s` aus:
- LED sofort AUS, Pumpe sofort AUS, alle Ventile AUS, **Abluft EIN**
- Fehlerflag `RS485_WATCHDOG` (error_bitmask Bit 0)
- Kein zwingender manueller Neustart nötig
- Nach Wiederkehr: kontrollierte Synchronisierung, **keine** automatische
  Fortsetzung einer unterbrochenen Bewässerung ohne neue Befehlssequenz.

Ein Ausgangsbefehl wird nur akzeptiert, wenn: Registerwerte gültig, Sequenz neu,
Watchdog aktiv, keine lokale Sperre, Pumpen-/Ventillogik plausibel.

## Sensorausfall Gewächshaus

LED AUS/auf sichere Grenze, Befeuchter AUS, Entfeuchter AUS, Bewässerung
gesperrt, Abluft EIN, Umluft auf feste sichere Leistung, sichtbarer Alarm.
Raumsensor ersetzt den Gewächshaussensor **nicht** automatisch.

## Bewässerung

Nur ein Ventil gleichzeitig (Default). Keine Pumpe ohne offenes Ventil, kein
Ventil ohne gültige Sequenz. Max. Ventil-/Pumpen-/Tageslaufzeit. Abbruchknopf.
Kommunikationsausfall beendet Bewässerung. Neustart setzt Sequenz nicht fort.

## Alarme

Sicherheitskritische Alarme lassen sich **quittieren, aber nicht deaktivieren**
— die zugrunde liegende Schutzaktion bleibt aktiv, bis die Ursache weg ist.

## Persistenz-Regeln

Nicht automatisch wiederherstellen: aktive Ventile/Pumpe, laufende Bewässerung,
LED-EIN, manuelle Overrides, Notfallquittierungen, angenommener IR-Zustand.
