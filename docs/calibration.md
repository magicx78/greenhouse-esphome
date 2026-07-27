# Kalibrierung (calibration.md)

## HX711 / TAL220 Wägezelle

1. **Tara** ohne Last (leerer Waageaufbau). Rohwert notieren = Nullpunkt.
2. Bekanntes Gewicht auflegen (z. B. 1000 g).
3. `Kalibrierfaktor = (Rohwert_last − Rohwert_null) / bekanntes_Gewicht`.
4. In ESPHome über `weight.yaml` (calibrate_linear) hinterlegen; Werte werden
   in `global`/Flash persistiert (siehe persistence).
5. **Keine automatische Tara**, wenn ein Topf auf der Waage steht.
6. Überlast-Alarm bei > Nennlast (10 kg) setzen.

Filter: Median → gleitender Mittelwert → Ausreißerunterdrückung. Driftkorrektur
nur im ausdrücklich aktivierten Kalibriermodus.

## Servo / LED-Dimmer

- Erst **ohne** mechanische Kopplung sichere Pulsweiten finden.
- `servo_min_level` / `servo_max_level` = TODO_CALIBRATE: die Endpunkte, die den
  Dimmer über seinen realen Regelweg fahren, **ohne** an die mechanischen
  Endanschläge zu drücken.
- Totzone konfigurieren, langsame Bewegung, max. Änderung/min.
- Servo nach Erreichen der Position deaktivieren (kein Dauerbrummen/-last).
- Bei ungültiger Kalibrierung: **LED-Relais bleibt AUS**.

## VPD / Blatt-Offset

- `leaf_temperature_offset` (Default −1,0 K) grob nach Bestand/Beleuchtung.
- Solange kein echter Blattsensor vorhanden ist: Wert bleibt **Schätzung**.

## BLE-Plausibilität

- Timeout je Sensor setzen (Default 120 s), Sprungfilter aktivieren.
- Nach Formatbestimmung (ATC/PVVX/BTHome) ggf. Plattform in `ble-sensors.yaml`
  anpassen.
