# CLAUDE.md — greenhouse-esphome

## Worum es geht

Automatisiertes Indoor-Gewächshaus (220 × 100 × 100 cm, ≈2,2 m³) auf Basis von
**ESPHome (3 Knoten) + Home Assistant**. Geregelt werden: Licht (400-W-LED über
Koppelrelais + Servo am mechanischen Dimmer), Temperatur, Luftfeuchte, **VPD**,
Umluft (2× PWM-Lüfter), Abluft (230 V über Koppelrelais), Bewässerung
(8 Ventile + Pumpe), Luftbefeuchtung (Oraimo OHM-H01 per IR) und optional ein
Entfeuchter (WLAN-Steckdose). HA (`http://10.10.10.205:8123`, Dev-Server auf
Proxmox200/VM101) ist nur Visualisierung/Komfort — **die Grundregelung muss
lokal ohne HA/WLAN/API funktionieren**.

## Architektur (FESTGELEGT — nicht ohne Grund ändern)

| Knoten | Hardware | Rolle |
|--------|----------|-------|
| `greenhouse-hmi` | Waveshare ESP32-S3-Touch-LCD-4 (480×480, GT911, ESP-IDF, LVGL 9, `mipi_rgb` Modell `WAVESHARE-4-480x480`) | LVGL-UI, Supervisor-Zustandsautomat, **Modbus-RTU-Client**, HA-Anbindung, SNTP/HA-Zeit |
| `kc868-a16` | KinCony KC868-A16 (ESP32, 4× PCF8574, LAN8720, RS485 GPIO13/16) | Ventile 1–8 (Y01–08), Pumpe (Y09), LED-Relais (Y10), Abluft-Relais (Y11), **Modbus-RTU-Server**, Watchdog, sichere Bootzustände |
| `greenhouse-io` | ESP32-S3 DevKit (Board noch offen) | 2× Lüfter-PWM 25 kHz + Tacho (PCNT), HX711+TAL220, IR TX/RX (RMT), Servo, BLE (2× Xiaomi ATC/PVVX), später 2× ADS1115 |

Der dritte Knoten ist **zwingend** (Pin-Audit: KC868 hat keine freien schnellen
GPIOs, alle Ausgänge hinter I²C-Expander; HMI durch RGB-Panel+PSRAM belegt).
Begründung: `docs/architecture.md`, Audit: `docs/hardware-pin-audit.md`.

## Sicherheits-Invarianten (NIEMALS verletzen)

1. KC868 schaltet **nie** direkt 230 V — nur 12-V-Spulen von Koppelrelais/Schützen.
2. Boot-Zustand: alles AUS, Abluft EIN (implizit: Watchdog startet „not ok").
3. Heartbeat-Watchdog (Register 0x0004/0x0022): Ausfall ⇒ LED/Pumpe/Ventile AUS,
   Abluft EIN, Flag `RS485_WATCHDOG`. Keine Auto-Fortsetzung der Bewässerung.
4. Pumpe nur mit ≥1 offenem Ventil; Default max. 1 Ventil gleichzeitig.
5. Kein `restore_mode: ALWAYS_ON` für Pumpe/Ventile/LED; keine Wiederherstellung
   gefährlicher Zustände nach Neustart.
6. Sensorfehler (NaN/unplausibel/veraltet) ⇒ sicherer Rückfall (EMERGENCY).
7. LED nur bei gültiger Servo-Kalibrierung (`g_servo_cal_valid`).
8. **Keine GPIO-Nummern raten** — nur aus Schaltplan/Audit. `TODO_AFTER_PIN_AUDIT`
   ist eine bewusste Sperre (Build-Guard: `tests/check_no_todo.py`).
9. Keine IR-Codes erfinden — nur gelernte Codes aus `docs/ir-codes.md`.

## Kernprinzip der Codebasis

Die sicherheitskritische Logik existiert **doppelt und muss synchron bleiben**:
- `tests/ghlib.py` = ausführbare Spezifikation (reine Python, pytest-verifiziert)
- `components/greenhouse_controller/vpd_math.h` + `.cpp` = 1:1-C++-Spiegel

**Jede Änderung an Regelung/Arbitrierung/Registerplan: zuerst ghlib.py + Tests
anpassen (pytest grün), dann C++ nachziehen.** Registerplan:
`docs/rs485-register-map.md` (überlappungsfrei, getestet). Regelstrategie:
prioritätsbasierter Zustandsautomat (`docs/control-strategy.md`) — keine
konkurrierenden PIDs.

## Stand (Juli 2026)

✅ Fertig und verifiziert:
- Projektstruktur komplett (nodes/, packages/, components/, docs/, tests/, deploy/)
- Kernlogik: **32/32 pytest grün** (VPD/Psychrometrie, Zustandsautomat,
  Registerplan, Ausgangs-Arbitrierung/Interlocks)
- KC868-Node vollständig mit bestätigten Pins (Modbus-Server, Watchdog, PCF8574)
- HMI-Node mit mipi_rgb/GT911/LVGL-Grundgerüst + Modbus-Client + Supervisor
- greenhouse-io-Node (Lüfter/HX711/IR/Servo) mit TODO-Pin-Platzhaltern
- Alle 9 Doku-Dateien, Build-Guard, Deploy-Skript + HAOS-Wrapper

⏳ Offen (nächste Schritte, in dieser Reihenfolge):
1. `bash deploy/install-dev-server.sh` auf dem Dev-Server → `esphome config
   nodes/kc868-a16.yaml` muss OK sein; Fehler fixen falls Schema-Drift
2. `esphome compile nodes/kc868-a16.yaml` → erster Flash (S2 + 12 V)
3. Hardware-Angaben schließen (siehe README „Noch benötigte reale Messwerte"):
   Waveshare-Revision, HMI-RS485/Touch-Pins, greenhouse-io-Board + Pins,
   Lüfter-Datenblatt, BLE-Format/MACs, Servo-Kalibrierung, IR-Codes lernen
4. HMI-LVGL ausbauen: bisher nur Übersichtsseite — es fehlen die Seiten Klima,
   Licht, Lüfter, Bewässerung, Gewicht, Sensoren, Kalibrierung, Diagnose,
   Einstellungen (Muster in `nodes/greenhouse-hmi.yaml`)
5. Inbetriebnahme streng nach `docs/commissioning.md` Phase 1–11

## Zukunft / Roadmap

- Gewichtsgesteuerte Bewässerung (Start-/Zielgewicht, Versickerungszeit)
- 2× ADS1115 + 8 kapazitive Topffeuchtesensoren (`packages/soil-moisture-future.yaml`)
- Entfeuchter-Integration je nach Steckdose (Priorität: ESPHome-flash > Tasmota/
  MQTT > lokale LAN-API > HA-Entity; Cloud nie für Kernregelung)
- Tag/Nacht-VPD-Profile, LVGL-Charts (Messwert-Historie), 24-h-Logging-Auswertung
- Echter Blatttemperatursensor (dann Blatt-VPD keine Schätzung mehr)

## Workflows / Kommandos

```bash
python3 -m pytest tests/ -q            # Kernlogik (muss immer grün sein)
python3 tests/check_no_todo.py         # Build-Guard (blockt offene Pin-TODOs)
esphome config nodes/<node>.yaml       # Schema-Validierung
esphome compile nodes/<node>.yaml      # Build (HMI: ESP-IDF+LVGL, dauert)
esphome run nodes/<node>.yaml          # Flash + Logs
```

Setup: `secrets.example.yaml`→`secrets.yaml`, `substitutions.example.yaml`→
`substitutions.yaml`. Nodes ziehen `../substitutions.yaml` als Package;
`nodes/secrets.yaml` ist ein Shim auf die Root-Secrets. Deploy-Details:
`deploy/README-deploy.md`.

## Kontext im Dach-Projekt (Hardware-Doku — falls lokal vorhanden)

Idealerweise lebt dieses Repo im Ordner `Gewaechshaus-Control/` neben den
Hardware-Doku-Ordnern:
- `01_Steuerung_KinCony-KC868-A16/doku/` — offizieller Schaltplan, Pinout-PDF,
  ESPHome-Referenzkonfig, Datenblätter (PCF8574, LAN8720A, ESP32-WROOM-32)
- `02_Display_Waveshare-ESP32-S3-Touch-LCD-4/doku/` — Wiki-Manual (PDF),
  Schaltpläne V2/V3.0/V4.0, Datenblätter (ESP32-S3, GT911, …)
- `03_Waegesensor_HX711/doku/` — HX711-Datenblatt, TAL220, Hookup-Guide
- `04_Luftbefeuchter_Oraimo-OHM-H01/doku/` — Bedienungsanleitung kompakt

**Bekannte Ablageorte (Stand 2026-07-27):**
- HA-Dev-Server (10.10.10.205): `/share/Gewaechshaus-Control/`
- Windows: `C:\Users\magic\OneDrive\Dokumente\Gewaechshaus-Control\`

Falls beides nicht erreichbar: Primärquellen online — Waveshare-Wiki
`ESP32-S3-Touch-LCD-4`, KinCony `KC868-A16-schematic.pdf`,
devices.esphome.io/devices/kincony-kc868-a16. **Fehlende Doku ist niemals ein
Grund, GPIO-Nummern zu raten** (Invariante 8 gilt unverändert).
