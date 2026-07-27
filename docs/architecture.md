# Architekturentscheidung

## Ergebnis: 3-Knoten-Architektur (verpflichtend, nicht künstlich erzwungen)

| Knoten | Hardware | Rolle |
|--------|----------|-------|
| `greenhouse-hmi` | Waveshare ESP32-S3-Touch-LCD-4 | LVGL-HMI, Supervisor/Regelung, **Modbus-RTU-Client**, HA-Anbindung, Zeitquelle |
| `kc868-a16` | KinCony KC868-A16 | Leistungsausgänge (Ventile, Pumpe, LED-/Abluft-Koppelrelais), **Modbus-RTU-Server**, Ausgangs-Watchdog, sichere Bootzustände |
| `greenhouse-io` | ESP32-S3 DevKit (empfohlen) **oder** klassischer ESP32 | Lüfter-PWM + Tacho, HX711, IR-TX/RX, Servo, BLE-Thermometer, später ADS1115 |

## Begründung (aus der Pin-/Ressourcenprüfung, Details in `hardware-pin-audit.md`)

**Warum der KC868-A16 die Aktorik-Peripherie NICHT übernehmen kann:**
Der KC868-A16 hat laut offiziellem Schaltplan/ESPHome-Referenz praktisch alle
nutzbaren GPIOs fest belegt:
- I²C (GPIO4/5) → 4× PCF8574 (Ein-/Ausgänge)
- RS485 (GPIO13 TX / GPIO16 RX) → Modbus-Bus zum HMI
- Ethernet LAN8720 (GPIO23/18/17 + interne RMII-Pins GPIO19/21/22/25/26/27)
- 433 MHz (GPIO2/15), HT1–HT3 (GPIO32/33/14), Analog A1–A4 (GPIO36/34/35/39, **nur Eingänge**)

→ Es bleiben **keine** freien, für schnelle Signale geeigneten GPIOs für
25-kHz-PWM, Tacho-Pulse-Counter, HX711-Bitbang, IR-RMT oder Servo.
Alle 16 Ausgänge liegen zudem **hinter dem PCF8574-I²C-Expander** und sind
damit grundsätzlich ungeeignet für schnelle/zeitkritische Signale.

**Warum das Waveshare-HMI die Peripherie NICHT übernehmen kann:**
Das 480×480-RGB-Panel belegt über den `mipi_rgb`-Treiber sehr viele GPIOs
(16 RGB-Datenleitungen + HSYNC/VSYNC/DE/PCLK), dazu GT911-Touch (I²C),
Backlight und der Octal-PSRAM (belegt mehrere GPIOs im Bereich GPIO33–37).
Freie, sichere GPIOs sind rar; die vorhandene RS485-Schnittstelle wird für
Modbus zum KC868 gebraucht. Das Display soll außerdem nicht durch
zeitkritische ISR-Last (Tacho, IR, HX711) im LVGL-Rendering gestört werden.

**Konsequenz:** Ein dedizierter dritter Knoten `greenhouse-io` ist die
elektrisch saubere und wartbare Lösung. Er hält alle zeitkritischen und
analogen Funktionen an frei zugänglichen GPIOs und entlastet HMI und KC868.

## Ausfallsicherheit / lokale Autonomie

- **Grundregelung ohne HA/WLAN:** Der Supervisor läuft auf dem HMI (lokal,
  ohne API). Sollwerte/Modus sind am Touch bedienbar. HA ist nur Komfort.
- **Modbus-Heartbeat HMI→KC868:** Fällt der HMI-Heartbeat aus, geht der KC868
  eigenständig in den Failsafe (LED/Pumpe/Ventile AUS, Abluft EIN).
- **greenhouse-io Notfalllüfter:** `greenhouse-io` hat eine lokale
  Übertemperatur-Notlogik für die Lüfter, die auch ohne HMI greift
  (eigener BLE- bzw. lokaler Temperatursensor als Trigger, konfigurierbar).
- **Schichtung der Regelung:** ein prioritätsbasierter Zustandsautomat
  (siehe `control-strategy.md`), keine gegeneinander arbeitenden PIDs.

## Kommunikationswege

```
        Home Assistant (10.10.10.205:8123)  ── optional, Komfort/Visualisierung
              │ (ESPHome native API, WLAN/LAN)
              │
   ┌──────────┴───────────┐         Modbus RTU (RS485, 19200 8N1)
   │   greenhouse-hmi     │◀───────────────────────────────────┐
   │ (Supervisor + LVGL)  │                                     │
   └──────────┬───────────┘                                     │
              │ ESPHome API / HA (Statusaustausch)              ▼
   ┌──────────┴───────────┐                          ┌────────────────────┐
   │    greenhouse-io     │                          │     kc868-a16      │
   │ Lüfter/HX711/IR/Servo│                          │ Ventile/Pumpe/LED  │
   └──────────────────────┘                          │ Modbus-Server      │
                                                      └────────────────────┘
```

Hinweis: HMI↔greenhouse-io tauschen unkritische Werte über die HA-API bzw.
`homeassistant`-Sensoren aus. Die **sicherheitskritische** Aktorik
(Ventile/Pumpe/LED/Abluft) läuft ausschließlich über den deterministischen
Modbus-Pfad HMI→KC868 mit Heartbeat/Watchdog.

## Testbare Kernlogik

Die sicherheitskritische Logik (VPD, Zustandsautomat, Registerplan,
Ausgangs-Arbitrierung/Interlocks) ist als reine Referenz in
`tests/ghlib.py` implementiert und mit `pytest` verifiziert (32 Tests grün).
Die C++ External Component `components/greenhouse_controller` spiegelt diese
Logik 1:1 (`vpd_math.h`).
