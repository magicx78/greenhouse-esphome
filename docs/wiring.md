# Verdrahtung (wiring.md)

> ⚠️ Alle 230-V-Arbeiten nur durch eine Elektrofachkraft. Kleinspannung (SELV)
> und Netzspannung strikt getrennt führen. Siehe `safety.md`.

## 1. RS485 / Modbus (HMI ↔ KC868-A16)

- Verdrilltes Paar A/B (Twisted Pair), kurze Stichleitungen.
- **120 Ω Abschluss nur an beiden Busenden** (HMI-Ende und KC868-Ende), sonst
  keine weiteren Abschlusswiderstände.
- Gemeinsame Signal-GND-Referenz zwischen den Boards, wenn nicht galvanisch
  getrennt (dünne GND-Ader mitführen).

```
HMI RS485  A ────────────────── A  KC868-A16 RS485
           B ────────────────── B
          GND ───────(ref)────── GND
  [120Ω zwischen A/B am HMI-Ende]     [120Ω zwischen A/B am KC868-Ende]
```

KC868-Pins bestätigt: TX=GPIO13, RX=GPIO16 (Transceiver on-board, DE/RE
automatisch). HMI-UART/DE-Pins: `hmi_rs485_*` = TODO_AFTER_PIN_AUDIT.

## 2. KC868-A16 Ausgänge (12/24 V Kleinspannung)

| Klemme | Last | Hinweis |
|--------|------|---------|
| Y01–Y08 | Magnetventile 12 V | Freilaufdiode an der Spule, falls nicht integriert |
| Y09 | Pumpe 12 V | ggf. über separates Leistungsrelais; Freilaufdiode |
| Y10 | Spule Koppelrelais → LED-NT 230 V | KC868 schaltet nur die 12-V-Spule |
| Y11 | Spule Koppelrelais/Schütz → Abluft 230 V | KC868 schaltet nur die 12-V-Spule |

MOSFET-Ausgänge schalten gegen GND (Low-Side). Lastversorgung 12 V extern,
gemeinsame GND mit KC868.

## 3. greenhouse-io Peripherie (Pins TODO_AFTER_PIN_AUDIT)

### 3.1 4-Draht-Lüfter (PC-Prinzip, Annahme — TODO bestätigen)
```
Lüfter:  +12V ── 12V-Netzteil
         GND  ── gemeinsame GND
         PWM  ── ESP GPIO (LEDC 25 kHz)   [Open-Drain am Lüfter; Pin nicht direkt belasten]
         TACH ── ESP GPIO (PCNT) + Pull-up 10k auf 3,3V
```
Tacho ist Open-Collector → **Pull-up auf 3,3 V zwingend**. Kein 12-V-Signal an
den ESP! (Bei 12-V-Tacho: Pegelwandler/Spannungsteiler nötig.)

### 3.2 HX711 + TAL220
```
Wägezelle  Rot→E+  Schwarz→E-  Weiß→A-  Grün→A+   (an HX711)
HX711  VCC→5V  GND→GND  DT→ESP GPIO  SCK→ESP GPIO
```

### 3.3 IR
```
IR-RX (mit Demodulator, z.B. TSOP38238):  OUT→ESP GPIO(RMT-RX)  VCC→3,3V  GND
IR-TX (IR-LED): ESP GPIO(RMT-TX) → Vorwiderstand → Basis Transistor → IR-LED → +5V
```
IR-LED **nie** direkt am GPIO — Transistortreiber verwenden.

### 3.4 Servo (verstellt mechanischen LED-Dimmer)
```
Servo: +5V (separat, ausreichend Strom)  GND(gemeinsam)  Signal→ESP GPIO(LEDC 50Hz)
```
Endanschläge kalibrieren (siehe `calibration.md`), nicht dauerhaft anfahren.

## 4. Masse-Konzept

Gemeinsame GND für alle 12-V-Kleinspannungskreise und die ESP-Knoten dort, wo
Signale ausgetauscht werden (RS485-Referenz, Tacho, IR). 230-V-PE **niemals**
schalten und nicht mit SELV-GND vermischen.
