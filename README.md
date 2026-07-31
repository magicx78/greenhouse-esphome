# 🌱 greenhouse-esphome — Automatisiertes Indoor-Gewächshaus

Vollständiges, wartbares ESPHome-Projekt (3 Knoten) für ein Gewächshaus
(220 × 100 × 100 cm, ≈2,2 m³). Regelt Licht, Temperatur, Luftfeuchte, VPD,
Umluft, Abluft, Bewässerung und Luftbefeuchtung weitgehend autonom. Home
Assistant (`http://10.10.10.205:8123`, HA-Dev-Server) dient Visualisierung/
Fernsteuerung — die **Grundregelung läuft lokal auch ohne HA/WLAN/API**.

> Status: Kernlogik **verifiziert** (32 pytest-Tests grün). YAML nach aktuellem
> ESPHome-Schema (2026.x) erstellt und review-geprüft. **Voller `esphome
> compile` auf dem HA-Dev-Server** durchführen (siehe unten). Offene
> Hardware-Details sind als sichtbare `TODO_AFTER_PIN_AUDIT` markiert und durch
> einen Build-Guard gegen versehentliches Produktiv-Flashen gesperrt.

## Architektur (3 Knoten — Begründung in docs/architecture.md)

| Knoten | Hardware | Aufgabe |
|--------|----------|---------|
| `greenhouse-hmi` | Waveshare ESP32-S3-Touch-LCD-4 | LVGL-HMI, Supervisor/Regelung, Modbus-**Client**, HA, Zeit |
| `kc868-a16` | KinCony KC868-A16 | Ventile/Pumpe/LED-/Abluft-Koppelrelais, Modbus-**Server**, Watchdog, sichere Bootzustände |
| `greenhouse-io` | ESP32-S3 DevKit | Lüfter PWM/Tacho, HX711, IR TX/RX, Servo, BLE, später ADS1115 |

Der dritte Knoten ist **zwingend**: am KC868-A16 sind alle nutzbaren GPIOs
belegt (I²C-Expander, RS485, Ethernet, 433 MHz, HT1–3, A1–4), das Waveshare-HMI
ist durch RGB-Panel + PSRAM stark belegt. Details: `docs/hardware-pin-audit.md`.

## Projektstruktur

```
greenhouse-esphome/
├── README.md
├── secrets.example.yaml          → secrets.yaml
├── substitutions.example.yaml    → substitutions.yaml (TODOs ausfüllen!)
├── nodes/         greenhouse-hmi.yaml · kc868-a16.yaml · greenhouse-io.yaml
├── packages/      common · diagnostics · safety · climate-control · irrigation ·
│                  lighting · fans · ble-sensors · weight · soil-moisture-future
├── components/greenhouse_controller/   (External Component: vpd_math.h + C++)
├── docs/          architecture · hardware-pin-audit · wiring · power-distribution ·
│                  rs485-register-map · control-strategy · commissioning ·
│                  calibration · safety · ir-codes
└── tests/         ghlib.py · test_vpd · test_state_machine · test_register_map ·
                   check_no_todo.py
```

## Setup

```bash
cp secrets.example.yaml secrets.yaml
cp substitutions.example.yaml substitutions.yaml
# substitutions.yaml editieren: Revisionen, MACs, Pins (nach Pin-Audit), Kalibrierung
```

Die Nodes binden `../substitutions.yaml` bereits als Package ein (Node-eigene
Substitutions gewinnen bei Konflikt). `nodes/secrets.yaml` ist ein Shim auf die
zentrale `secrets.yaml` im Projekt-Root — nichts weiter nötig.

**Deploy auf den HA-Dev-Server:** siehe `deploy/README-deploy.md`
(Weg A: HAOS-Add-on mit Wrapper-Dateien · Weg B: CLI-venv per
`bash deploy/install-dev-server.sh`).

## Validieren, Testen, Kompilieren

```bash
# 1) Kernlogik (läuft überall, ohne ESPHome):
python3 -m pytest tests/ -q

# 2) Build-Guard (blockt offene Pin-/Kalibrier-TODOs):
python3 tests/check_no_todo.py

# 3) ESPHome-Schema prüfen (auf dem HA-Dev-Server):
esphome config nodes/kc868-a16.yaml
esphome config nodes/greenhouse-hmi.yaml
esphome config nodes/greenhouse-io.yaml

# 4) Kompilieren/Flashen (HA-Dev-Server 10.10.10.205):
esphome compile nodes/kc868-a16.yaml
esphome compile nodes/greenhouse-hmi.yaml
esphome compile nodes/greenhouse-io.yaml
```

> Hinweis: `esphome config` schlägt absichtlich fehl, solange
> `TODO_AFTER_PIN_AUDIT`-Platzhalter als Pins stehen — das ist die Sperre.

> Auf dem HAOS-Dev-Server laufen die `esphome`-Kommandos per
> `sudo docker exec app_5c53de3b_esphome-dev esphome …` — Details und
> Einrichtung: `deploy/README-deploy.md` (Weg A). Das Präfix hat mit dem
> Supervisor-Umbau von `addon_` auf `app_` gewechselt; im Zweifel
> `sudo docker ps` fragen statt raten.

## Knoten ansprechen

Die Knoten hängen an der dynamischen DHCP-Vergabe und haben ihre Adressen schon
einmal gewechselt (KC868 .123 → .126, HMI .184 → .179 — die .184 gehört
inzwischen einem fremden Gerät). **Deshalb für OTA und Logs die mDNS-Namen
benutzen, nicht die IP:**

```bash
esphome logs nodes/greenhouse-hmi.yaml --device greenhouse-hmi.local
esphome run  nodes/kc868-a16.yaml     --device kc868-a16.local
```

Home Assistant findet die Knoten ohnehin per zeroconf; beide sind auf dem
Dev-Server (10.10.10.205) eingebunden.

## Verlaufsdiagramm auf dem Panel

Die Seite „Verlauf" zeigt Temperatur und Feuchte über 24 h als Kurven, dazu eine
rote Kennlinie mit dem **damals** eingestellten Sollwert und die Extremwerte
dieser 24 h. Ein Knopf schaltet zwischen beiden Größen um und wechselt dabei
Kurvenbezug, rote Kennlinie und die Wirkung der −/+-Tasten gemeinsam.

**LVGL-Chart ist in ESPHome nicht vorgesehen.** Es gibt kein `chart`-Widget, und
die generierte `lv_conf.h` setzt `LV_USE_CHART` auf 0. Freigeschaltet wird es
über `esphome: platformio_options: build_flags: ["-DLV_USE_CHART=1"]` —
`lvgl/__init__.py` durchsucht die Build-Flags nach `-DLV_USE_*` und lässt so
markierte Defines stehen. Aufgebaut wird das Chart in `on_boot` über die
LVGL-C-API. **Wird das Flag entfernt, bricht der Build mit undefinierten
`lv_chart_*`-Symbolen ab.**

Datenhaltung: 288 Fenster à 5 min als `int32_t`-Ringpuffer in Zehnteln, per
`lv_chart_set_series_ext_y_array` direkt an die Serien gebunden. Die Kurve zeigt
den Fenstermittelwert; die Min/Max-Zahlen kommen aus separat mitgeführten echten
Fensterextremen, damit eine kurze Spitze nicht in der Mittelung verschwindet.
Fenster ohne Messwert bleiben `LV_CHART_POINT_NONE` — die Linie reißt sichtbar
ab, statt einen Sensorausfall als stabile Phase auszugeben. Der Puffer liegt im
RAM und wird bewusst **nicht** persistiert (288 Fenster alle 5 min in den Flash
wären ~105.000 Schreibzyklen im Jahr).

### Backfill aus Home Assistant (optional, rein additiv)

Nach einem Neustart ist der Puffer leer. Auf der **Dev**-HA füllen ihn
`script.greenhouse_hmi_verlauf_nachladen` und die Automation
„Gewächshaus HMI: Verlauf nach Neustart nachladen" über `recorder.get_statistics`
(`period: 5minute`, `types: [mean, min, max]`) und die beiden ESPHome-Actions
`backfill_temp` / `backfill_hum`.

**Die Grundregelung hängt an keiner Stelle daran.** Fehlt HA, baut sich die Kurve
einfach ab Start neu auf. Zwei Fallen sind dort fest verdrahtet:

- `units: {temperature: "°C"}` ist **Pflicht** — HA führt den Gewächshaus-Sensor
  in Fahrenheit (84,7 °F bei 29,3 °C am Gerät) und lieferte sonst 84er-Werte.
- Der Recorder lässt Fenster ohne Daten **weg**. Die Zeilen sind also nicht
  lückenlos; jede bringt deshalb ihr Alter in 5-Minuten-Schritten mit, sonst
  verschöbe sich die ganze Kurve.

Die rote Kennlinie lässt sich nicht nachladen: `number`-Entitäten haben kein
`state_class`, HA führt für sie keine Statistik. Sie beginnt daher am
Startzeitpunkt des Panels.

## Flash-Reihenfolge (Erstinbetriebnahme)

1. `kc868-a16` zuerst (USB, S2-Taster + 12 V, Flash — siehe doku/KC868-Manual).
2. `greenhouse-io` (ESP32-S3 DevKit über USB).
3. `greenhouse-hmi` (Waveshare über USB-C).

Danach dem stufenweisen **Inbetriebnahmeplan** folgen: `docs/commissioning.md`
(Phase 1–11). **Erst Prüflampen, dann echte Lasten, 230 V zuletzt.**

## Sicherheit (Kurzfassung — Details in docs/safety.md)

- KC868 schaltet **niemals** direkt 230 V — nur 12-V-Koppelrelais/Schütze.
- Sichere Bootzustände; Heartbeat-Watchdog → Failsafe (Abluft EIN, Rest AUS).
- Not-Aus soll gefährliche Lasten **hardwareseitig** trennen.
- Bewässerungs-Interlocks (nur 1 Ventil, keine Pumpe ohne Ventil, Timeouts).

## Modbus-Registerplan

Siehe `docs/rs485-register-map.md` (überlappungsfrei, getestet).
`19200 8N1`, Server-Adresse 1, HMI=Client, KC868=Server.

### Offene Abweichung: Sequenzregister 0x0020

Der Registerplan nennt unter „Arbitrierung / Interlocks" als Regel 5, ein Befehl
werde nur akzeptiert, wenn unter anderem **die Sequenz neu** ist. Das ist derzeit
weder implementiert noch benutzt: Der HMI schreibt `command_sequence` (0x0020)
nie, `g_cmd_seq`/`g_ack_seq` in `packages/safety.yaml` bleiben auf 0, und
`greenhouse::arbitrate_outputs()` kennt gar keinen Sequenzparameter. Das
Fehlerbit `SEQUENCE_STALE` (Bit 2) wird nie gesetzt.

Praktisch schützt heute allein der Heartbeat-Watchdog (0x0004/0x0022) — das ist
Invariante 3 und funktioniert. Die Sequenzprüfung wäre der zusätzliche Schutz
gegen *wiederholte alte* Befehle. Sie nachzuziehen ist eine Änderung an der
Arbitrierungslogik und folgt deshalb dem Kernprinzip: **erst `tests/ghlib.py`
plus Tests, dann der C++-Spiegel, dann `safety.yaml` und der HMI-Client.**

## Noch benötigte reale Messwerte / Hardwareangaben (Deliverable #14)

**Zwingend vor Produktivbetrieb:**
- [ ] Waveshare-Revision (V1–V4) ablesen → `waveshare_revision`
- [ ] KC868-A16-Revision ablesen → `kc868_revision`
- [ ] Waveshare Touch-I²C- und RS485-UART/DE-Pins der Revision (Schaltplan)
- [ ] greenhouse-io Board final wählen → alle `*_pin` GPIOs setzen
- [ ] Lüfter: Hersteller, Modell, Spannung, Nennstrom, PWM-Spez, Tacho-Pegel,
      Pulse/Umdrehung, max. m³/h (Annahme 12 V 4-Draht bestätigen)
- [ ] BLE-Thermometer: tatsächliches Broadcast-Format (ATC/PVVX/BTHome) per Log
- [ ] BLE-MAC-Adressen beider Sensoren
- [ ] HX711: DOUT/CLK-Pins + Kalibriergewicht; Kalibrierfaktor ermitteln
- [ ] IR-Codes des Oraimo lernen (docs/ir-codes.md) — keine Codes erfunden
- [ ] Servo: sichere min/max-Pulsweiten kalibrieren (`servo_*_level`)
- [ ] WLAN-Entfeuchter-Steckdose: Hersteller/Firmware/lokale Steuerbarkeit
      (ESPHome > Tasmota/MQTT > lokale LAN > HA-Entity > **keine** Cloud)
- [ ] 12-V-Netzteil-Budget aus realen Ventil-/Pumpen-Strömen

**Empfohlen:**
- [ ] Trockenlauf-/Tank-Leer-/Leck-/Durchflusssensor für Bewässerung
- [ ] Echter Blatttemperatursensor (dann ist Blatt-VPD keine Schätzung mehr)
- [ ] ADS1115 + korrosionsbeständige kapazitive Topffeuchtesensoren

## Verifikationsstand

- ✅ VPD/Psychrometrie, Zustandsautomat, Registerplan, Ausgangs-Arbitrierung:
  32 pytest-Tests grün (`tests/`), C++ spiegelt diese Logik (`vpd_math.h`).
- ⏳ `esphome config`/`compile`: auf dem HA-Dev-Server ausführen (LVGL/ESP-IDF/
  mipi_rgb-Toolchain). YAML ist schema-konform erstellt; kleinere
  Board-revisionsspezifische Anpassungen (Touch-I²C-, RS485-Pins) nach dem
  Pin-Audit vornehmen.
