# Inbetriebnahmeplan (commissioning.md)

Stufenweise, sicherheitsorientiert. **Erst wenn eine Phase sauber läuft, zur
nächsten.** Kein Produktivbetrieb, solange `TODO_AFTER_PIN_AUDIT`/`TODO_CALIBRATE`
offen sind (die Config verweigert sonst den produktiven Build, siehe README §Guard).

## Phase 1 — HMI nur USB
Kein Relais, keine Pumpe/Ventile, keine Netzspannung. Display + Touch testen
(`greenhouse-hmi`), LVGL-Seiten durchklicken.

## Phase 2 — RS485/Modbus
Register lesen/schreiben (0x0000 Protokollversion, 0x0002 Uptime). Heartbeat
0x0004 vom HMI, Watchdog testen: Bus absichtlich trennen → KC868 muss Failsafe
gehen (Abluft EIN, Rest AUS), `RS485_WATCHDOG` setzen.

## Phase 3 — KC868-Ausgänge mit Prüflampen
Nur LEDs/Prüflampen an Y01–Y11. Polarität, Bootzustände, Watchdogzustände
prüfen. Interlocks: Pumpe darf ohne Ventil nicht schalten.

## Phase 4 — Lüfter (greenhouse-io, ohne Klimaregelung)
PWM-Kennlinie erfassen, minimale Startleistung bestimmen, RPM prüfen,
Stall simulieren (Lüfter blockieren → Fehlerbit).

## Phase 5 — BLE-Sensoren
Paketformat bestimmen (ATC/PVVX/BTHome — siehe ble-sensors.yaml), Timeout und
Sensorausfall simulieren → sicherer Rückfall.

## Phase 6 — HX711
Tara, bekannte Gewichte, Kalibrierfaktor, Drift, Überlast (siehe calibration.md).

## Phase 7 — IR
Jeden Befehl lernen und einzeln testen (ir-codes.md), Shadow-State + Neustart.

## Phase 8 — Servo
Erst **ohne** mechanische Kopplung, dann Dimmer vorsichtig kalibrieren,
Endanschläge vermeiden.

## Phase 9 — Ventile/Pumpe/Interlocks
Ventile einzeln, Pumpe getrennt, Interlocks, Not-Aus.

## Phase 10 — 230-V-Koppelrelais/Schütze
Fachgerecht anschließen, **zuerst ohne Last** testen, dann LED und Abluft
einzeln.

## Phase 11 — Regelbetrieb
Temperatur-, VPD-, Bewässerungsautomatik. Mehrstündiger Probebetrieb, dann
≥24 h Logging.
