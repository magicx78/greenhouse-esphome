# Regelstrategie (control-strategy.md)

Kein Satz unabhängiger PIDs. Ein **prioritätsbasierter Zustandsautomat**
(Supervisor) entscheidet, welche Aktoren wie wirken. Implementiert und getestet
in `tests/ghlib.py` / `test_state_machine.py`, gespiegelt in der C++-Component.

## Betriebsmodi (Register 0x0023)

| Wert | Modus |
|------|-------|
| 0 | OFF |
| 1 | MANUAL |
| 2 | AUTO_TEMPERATURE |
| 3 | AUTO_VPD |
| 4 | IRRIGATION |
| 5 | EMERGENCY |
| 6 | MAINTENANCE |

## Prioritäten (höchste zuerst — überschreiben alles darunter)

1. **El./therm. Sicherheit** (Kommunikations-/Watchdog-Ausfall) → EMERGENCY:
   LED AUS, Pumpe/Ventile AUS, Abluft EIN, Umluft auf `fan_min`, Alarm.
2. **Sensorfehler** (Gewächshaussensor NaN/unplausibel/veraltet) → gleicher
   sicherer Rückfall, Bewässerung gesperrt.
3. **Maximaltemperatur** ≥ `emergency_temp` → EMERGENCY, beide Lüfter auf
   `fan_emergency`, Abluft EIN, LED AUS. ≥ `max_temp` → Abluft EIN, Lüfter hoch.
4. **Minimaltemperatur** ≤ `min_temp` → Kühlung/Abluft aus, Umluft `fan_min`.
5. **Kondensationsschutz** (T − Taupunkt < 1,5 K) → Abluft EIN, Entfeuchter EIN,
   Befeuchter AUS.
6. **Maximale Luftfeuchte** ≥ `max_humidity` → Abluft/Entfeuchter EIN.
7. **VPD-Regelung** (AUTO_VPD) bzw. Temperatur (AUTO_TEMPERATURE).
8. **Komfort/Energie**.

Temperaturgrenzen überschreiben **immer** die VPD-Regelung.

## Temperaturregelung

- Modulierbare Umluftlüfter: PI/PID (Anti-Windup), sanfte Rampen, max.
  Stellgrößenänderung/min. Umsetzung auf `greenhouse-io` (LEDC 25 kHz).
- 230-V-Abluft (KC868 Y11) **stufig** mit Hysterese, Mindestlauf-/-auszeit und
  begrenzter Schalthäufigkeit — **nicht** sekündlich schalten.

## VPD-Regelung (AUTO_VPD)

- Ziel `target_vpd` mit Totband `vpd_deadband`.
- Geglättete Sensorwerte, Änderungsbegrenzung, Mindestlaufzeiten, Anti-Windup.
- VPD zu niedrig (Luft zu feucht): Befeuchter AUS → Umluft ↑ → Abluft bei
  Bedarf → Entfeuchter nach Mindestwartezeit EIN.
- VPD zu hoch (Luft zu trocken): Entfeuchter AUS → Abluft ↓ (falls Temp erlaubt)
  → Befeuchter EIN → Umluft nicht ganz aus.
- Blatt-VPD als **Schätzung** (kein echter Blattsensor), Offset `leaf_offset`.

## Zeitproportionale Aktoren

Luftbefeuchter (IR) und Kompressor-Entfeuchter (WLAN-Steckdose) sind nicht
kontinuierlich modulierbar → **Zeitproportionalregelung** mit langen Fenstern +
Hysterese + Mindestlauf-/-auszeit, statt schneller Schaltzyklen.

## Profile (konfigurierbar, kein Profil ist universell „richtig")

`Keimling | Wachstum | Blüte | Benutzerdefiniert` — je Profil: Tag-/Nacht-VPD,
min/ziel/max-Temperatur, min/max-Feuchte, Lichtleistung, Umluft-Minimum.
Alle Werte über `number`/`select`/LVGL einstellbar.
