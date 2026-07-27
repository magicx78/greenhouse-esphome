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
- RS485: on-board Transceiver → **Modbus-Client-UART**. Revisionsabhängig.
  **Für V3.0 bestätigt (2026-07-27):**

  | Signal | GPIO | Quelle |
  |--------|------|--------|
  | RS485 RXD (ESP empfängt) | GPIO43 | Wiki-Manual S. 10/11, Beispiel `04_RS485_Test`: `Serial2.begin(115200, SERIAL_8N1, 43, 44)` |
  | RS485 TXD (ESP sendet) | GPIO44 | ebenda |
  | DE / Richtungsumschaltung | **entfällt** | Schaltplan V3.0: U7 = `MAX13487EESA+` (AutoDirection); nur `485_TXD`/`485_RXD` am Bauteil |

  ⚠️ GPIO43/44 sind auf dem ESP32-S3 zugleich die Standard-UART0-Konsole. Der
  Logger muss deshalb auf `USB_SERIAL_JTAG` (natives USB) laufen, sonst
  kollidiert er mit dem Modbus-UART.
- CAN: separater Transceiver `TJA1051T/3` (U6, Netze `CANTX`/`CANRX`) — im
  Projekt nicht verwendet, aber nicht mit RS485 verwechseln.
- Touch GT911: **TP_SDA=GPIO15, TP_SCL=GPIO7, TP_INT=GPIO16** (Schaltplan V3.0).
  `TP_RST` liegt nicht am Modul, sondern am I/O-Expander.
  ⚠️ GPIO8/GPIO9 sind **nicht frei** (R3 bzw. G5 des RGB-Panels) — eine frühere
  Fassung hatte sie als Touch-I²C geraten.

### Vollständige Modulbelegung V3.0 (aus dem Schaltplan ausgelesen, 2026-07-27)

| GPIO | Netz | GPIO | Netz |
|------|------|------|------|
| IO1 | LCD_SDA / MOSI | IO18 | R4 |
| IO2 | LCD_SCL / SCK | IO19 | ESP_USB_N |
| IO4 | MISO | IO20 | ESP_USB_P |
| IO5 | B1 | IO21 | B5 |
| IO7 | **TP_SCL** | IO38 | HSYNC |
| IO8 | R3 | IO39 | VSYNC |
| IO9 | G5 | IO40 | DE |
| IO10 | G4 | IO41 | LCD_PCLK |
| IO11 | G3 | IO42 | LCD_CS |
| IO12 | G2 | IO43 | **RS485_TX** → ESP **RX** |
| IO13 | G1 | IO44 | **RS485_RX** → ESP **TX** |
| IO14 | G0 | IO45 | B2 |
| IO15 | **TP_SDA** | IO46 | R1 |
| IO16 | **TP_INT** | IO47 | B4 |
| IO17 | R5 | IO48 | B3 |

Die RS485-Netznamen sind aus Sicht des **Transceivers** benannt: `485_TXD`
hängt an Pin 1 (`RO`, Receiver Output) des MAX13487 und speist damit den
ESP-Eingang. Deshalb ist `RS485_TX` (IO43) der **RX** des ESP — deckungsgleich
mit dem Wiki-Beispiel `Serial2.begin(115200, SERIAL_8N1, 43, 44)`.

**Fazit HMI:** Praktisch alle GPIOs sind durch RGB-Panel, Touch, USB und RS485
belegt. Für zusätzliche Peripherie bleibt am HMI nichts übrig — das bestätigt
die Notwendigkeit des dritten Knotens (`greenhouse-io`).
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
