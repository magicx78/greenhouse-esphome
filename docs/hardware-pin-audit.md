# Hardware-Pin-, Bus-, Speicher- und Timer-Audit

> Grundsatz: **Keine GPIO-Nummer wird geraten.** Bestätigte Pins stammen aus
> der offiziellen ESPHome-Geräteseite bzw. dem KinCony-Schaltplan (im
> Dach-Projekt unter `01_Steuerung_.../doku/`). Unbestätigte Pins sind als
> `TODO_AFTER_PIN_AUDIT` markiert und müssen an der **aufgedruckten
> Hardware-Revision** verifiziert werden, bevor produktiv geflasht wird.

## A. KC868-A16 — bestätigt (Quelle: ESPHome devices + KinCony-Schaltplan)

| GPIO | Funktion | Frei? |
|------|----------|-------|
| GPIO4 | I²C SDA (PCF8574-Bus) | belegt |
| GPIO5 | I²C SCL (PCF8574-Bus) | belegt (Strapping) |
| GPIO13 | RS485 TX | belegt |
| GPIO16 | RS485 RX | belegt |
| GPIO23 | Ethernet MDC | belegt |
| GPIO18 | Ethernet MDIO | belegt |
| GPIO17 | Ethernet CLK_OUT | belegt |
| GPIO19/21/22/25/26/27 | LAN8720 RMII (intern) | belegt |
| GPIO2 | 433 MHz RX (Strapping!) | belegt |
| GPIO15 | 433 MHz TX (Strapping!) | belegt |
| GPIO32/33/14 | Digitaleingänge HT1/HT2/HT3 | belegt |
| GPIO36/34/35/39 | Analog A1–A4 (**input-only**) | belegt |
| PCF8574 0x22/0x21 | Eingänge X01–X16 | I/O-Expander |
| PCF8574 0x24/0x25 | Ausgänge Y01–Y16 (MOSFET) | I/O-Expander |

**Fazit KC868-A16:** keine freien schnellen GPIOs; alle Ausgänge über I²C.
→ eignet sich ausschließlich für die langsame Leistungsschaltung (Ventile,
Pumpe, Koppelrelais) + Modbus-Server. **Ausgangs-Zuordnung** siehe unten.

### KC868-A16 Ausgangsbelegung (Y = MOSFET-Ausgang, schaltet 12/24 V Kleinspannung)

| Ausgang | Funktion | Output-Bit |
|---------|----------|-----------|
| Y01–Y08 | Ventil 1–8 (12 V Magnetventile) | 0–7 |
| Y09 | Bewässerungspumpe (12 V, ggf. über Koppelrelais) | 8 |
| Y10 | **Koppelrelais** 12 V → LED-Netzteil 230 V | 9 |
| Y11 | **Koppelrelais/Schütz** 12 V → Abluft 230 V | 10 |
| Y12–Y16 | Reserve | 11–15 |

> ⚠️ Y10/Y11 schalten **niemals** direkt Netzspannung — nur die Spule eines
> externen Koppelrelais/Schützes. Siehe `power-distribution.md` und `safety.md`.

## B. Waveshare ESP32-S3-Touch-LCD-4 — teils revisionsabhängig

`waveshare_revision: TODO` — auf der Platine aufgedruckte Revision (V1–V4)
prüfen und in `substitutions.example.yaml` eintragen.

Bestätigt/vorkonfiguriert durch ESPHome:
- Display: `display: platform: mipi_rgb, model: WAVESHARE-4-480x480`
  → **alle RGB-/Timing-Pins sind im Modell vordefiniert** (nicht manuell setzen).
- Touch: nativer `gt911`-Treiber am internen I²C des Boards.
- PSRAM: Octal-PSRAM (ESP32-S3, 8 MB) → im `esp32:`/`psram:`-Block aktivieren;
  belegt intern GPIOs im Bereich GPIO33–37 (nicht anderweitig verwenden).
- RS485: on-board Transceiver → **Modbus-Client-UART**. Die konkreten
  UART-/DE-Pins sind revisionsabhängig: `hmi_rs485_tx/rx/de: TODO_AFTER_PIN_AUDIT`
  (aus dem Schaltplan der vorliegenden Revision übernehmen).

> Da die freien GPIOs stark vom Panel/PSRAM belegt sind, übernimmt das HMI
> **keine** zeitkritische Peripherie (siehe architecture.md).

## C. greenhouse-io — freie Ressourcen (ESP32-S3 DevKit empfohlen)

Anforderungen und warum ESP32-S3-DevKit passt:
- **2× LEDC-PWM 25 kHz** für Lüfter → ESP32-S3 hat 8 LEDC-Kanäle. ✔
- **2× Pulse-Counter (PCNT)** für Tacho → S3 hat PCNT-Einheiten. ✔
- **HX711** (2 GPIO, Bitbang, unkritisch) ✔
- **IR-TX/RX über RMT** → S3 hat mehrere RMT-Kanäle. ✔
- **1× Servo** (LEDC 50 Hz) ✔
- **BLE** (Xiaomi-Thermometer) → S3 hat BLE. ✔  (klassischer ESP32 ebenso)
- **I²C** für spätere 2× ADS1115 ✔

Konkrete Pins bleiben **bewusst TODO_AFTER_PIN_AUDIT**, bis das reale
DevKit-Board feststeht. Empfehlung sichere GPIOs am S3-DevKit (Vorschlag, zu
bestätigen): PWM z. B. GPIO4/5, Tacho GPIO6/7 (mit 3,3 V Pull-up), HX711
GPIO15/16, IR-TX GPIO17, IR-RX GPIO18, Servo GPIO8, I²C GPIO9/10.
**Nicht verwenden:** Strapping-Pins GPIO0/3/45/46, USB-JTAG GPIO19/20,
und – bei Octal-PSRAM/Flash – GPIO26–32/33–37.

## D. Bus-Übersicht

| Bus | Knoten | Zweck |
|-----|--------|-------|
| RS485 / Modbus RTU | hmi ↔ kc868 | deterministische Aktorik + Heartbeat |
| I²C #1 | kc868 | PCF8574 Ein-/Ausgänge |
| I²C intern | hmi | GT911-Touch |
| I²C | greenhouse-io | (später) ADS1115 |
| RMT | greenhouse-io | IR TX/RX |
| LEDC | greenhouse-io | Lüfter-PWM (25 kHz), Servo (50 Hz) |
| PCNT | greenhouse-io | Lüfter-Tacho |
| BLE | greenhouse-io | Xiaomi-Thermometer |
| Ethernet | kc868 | optional LAN statt/zusätzlich zu WLAN |
| WLAN | hmi, greenhouse-io | HA-API |

## E. Strapping-/Boot-Pins (Vorsicht)

- KC868: GPIO2, GPIO15, GPIO5 werden mit `ignore_strapping_warning: true`
  genutzt (durch die Referenzkonfiguration abgedeckt).
- ESP32-S3: GPIO0, GPIO3, GPIO45, GPIO46 sind Strapping — für `greenhouse-io`
  meiden bzw. nur mit Bedacht als Ausgang nach Boot.

## F. Timer/Speicher

- HMI: LVGL9 + mipi_rgb benötigen PSRAM (8 MB Octal) → Framebuffer im PSRAM.
- LEDC/PCNT/RMT-Ressourcen ausschließlich auf `greenhouse-io` gebündelt, um
  Konflikte mit Display-Timing (HMI) und I²C-Expander (KC868) zu vermeiden.

## G. Offene Punkte (müssen vor Produktivbetrieb geschlossen werden)

- [ ] Waveshare-Revision (V1–V4) ablesen → `waveshare_revision`
- [ ] KC868-Revision ablesen → `kc868_revision`
- [ ] HMI RS485 UART-/DE-Pins aus Schaltplan der Revision → `hmi_rs485_*`
- [ ] greenhouse-io Board final wählen → alle `*_pin: TODO_AFTER_PIN_AUDIT`
- [ ] Lüfter-Datenblatt (PWM/Tacho/PPR) bestätigen (siehe fans.yaml TODO)
