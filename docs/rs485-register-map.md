# RS485 / Modbus-RTU Registerplan

Bus: **Modbus RTU**, `19200 8N1`, Server-Adresse `1`.
HMI = Client/Master, KC868-A16 = Server/Slave.
Registerbreite 16 Bit (Holding Registers), sofern nicht anders angegeben.
Der Plan ist überlappungsfrei (verifiziert durch `tests/test_register_map.py`).

## Holding Register

| Adresse | Name | Typ | R/W | Beschreibung |
|---------|------|-----|-----|--------------|
| 0x0000 | protocol_version | U16 | R | Protokollversion (=1) |
| 0x0001 | firmware_version | U16 | R | Major<<8 \| Minor |
| 0x0002 | server_uptime_s | U32 (0x0002–0x0003) | R | Server-Uptime in s |
| 0x0004 | last_master_heartbeat | U16 | W | Master schreibt inkrementierenden Zähler |
| 0x0005 | comm_status | U16 | R | Bitfeld Kommunikationsstatus |
| 0x0006 | error_bitmask | U16 | R | Fehlerbitmaske (siehe unten) |
| 0x0010 | requested_output_mask | U16 | W | vom Master angeforderte Ausgänge |
| 0x0011 | active_output_mask | U16 | R | **logisch** aktive Ausgänge (kein el. Nachweis!) |
| 0x0012 | allowed_output_mask | U16 | W | erlaubte Ausgänge (Freigabe) |
| 0x0013 | locked_output_mask | U16 | R | gesperrte Ausgänge (lokale Sperre) |
| 0x0020 | command_sequence | U16 | W | Befehls-Sequenznummer (monoton) |
| 0x0021 | acked_sequence | U16 | R | vom Server bestätigte Sequenznummer |
| 0x0022 | watchdog_time_s | U16 | W | Watchdog-Timeout in s |
| 0x0023 | operating_mode | U16 | W | Betriebsmodus (siehe control-strategy.md) |
| 0x0030 | valve_max_time_s | U16 | W | max. Ventil-Laufzeit |
| 0x0031 | pump_post_run_s | U16 | W | Pumpen-Nachlaufzeit |
| 0x0032 | pump_pre_run_s | U16 | W | Pumpen-Vorlaufzeit |
| 0x0033 | max_active_valves | U16 | W | max. gleichzeitig offene Ventile (Default 1) |

## Ausgangs-Bitbelegung (requested/active/allowed/locked)

| Bit | Ausgang |
|-----|---------|
| 0 | Ventil 1 |
| 1 | Ventil 2 |
| 2 | Ventil 3 |
| 3 | Ventil 4 |
| 4 | Ventil 5 |
| 5 | Ventil 6 |
| 6 | Ventil 7 |
| 7 | Ventil 8 |
| 8 | Pumpe |
| 9 | LED-Koppelrelais |
| 10 | Abluft-Koppelrelais |
| 11–15 | Reserve |

## comm_status (0x0005) Bits

| Bit | Bedeutung |
|-----|-----------|
| 0 | watchdog_ok |
| 1 | letzter Schreibzugriff gültig |
| 2 | Client jemals gesehen |

## error_bitmask (0x0006) Bits

| Bit | Fehler |
|-----|--------|
| 0 | RS485_WATCHDOG (Heartbeat-Timeout) |
| 1 | INVALID_REGISTER (Wert außerhalb Grenzen) |
| 2 | SEQUENCE_STALE (keine neue Sequenz) |
| 3 | LOCAL_LOCK aktiv |
| 4 | VALVE_MAX_TIME überschritten |
| 5 | PUMP_MAX_TIME überschritten |

## Wichtiger Hinweis zu `active_output_mask` (0x0011)

Der Wert bezeichnet **ausschließlich den intern gesetzten, logischen
Ausgangszustand** nach Arbitrierung (requested & allowed & ~locked +
Interlocks). Es ist **kein** Nachweis einer real fließenden Last oder eines
geschlossenen Kontakts — dafür fehlen Stromsensor/Hilfskontakt.

## Arbitrierung / Interlocks (Server-seitig, `write_lambda`)

Implementiert in `packages/safety.yaml` (KC868), gespiegelt in
`components/greenhouse_controller/vpd_math.h` und getestet in
`tests/test_register_map.py`:

1. Watchdog abgelaufen → alle gefährlichen Ausgänge AUS, **Abluft EIN**.
2. effektiv = requested & allowed & ~locked.
3. Ventil-Anzahl auf `max_active_valves` begrenzen (niedrigste Bits gewinnen).
4. Pumpe (Bit 8) nur wenn ≥1 Ventil offen (Trockenlauf-Interlock).
5. Befehl nur akzeptiert, wenn Register gültig **und** Sequenz neu **und**
   Watchdog aktiv **und** keine lokale Sperre.
