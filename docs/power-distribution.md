# Stromverteilung (power-distribution.md)

> ⚠️ 230-V-Seite nur durch Elektrofachkraft. Jede Lastgruppe eigene Sicherung,
> Berührungsschutz, Zugentlastung, geeignete Schutzart (Feuchtraum!).

## Spannungsebenen

| Ebene | Quelle | Verbraucher |
|-------|--------|-------------|
| 230 V AC | Netz (über FI/RCD + LS) | LED-Netzteil (400 W), Abluft-Lüfter, Entfeuchter (WLAN-Steckdose), Luftbefeuchter |
| 12 V DC | Netzteil ausreichend dimensioniert | KC868-Ausgänge, Ventile, Pumpe, Lüfter (12 V), Koppelrelais-Spulen |
| 5 V DC | Step-Down / USB | HX711, IR-TX-LED, Servo (eigene 5-V-Schiene mit Reserve) |
| 3,3 V | on-board Regler der ESPs | Logik, Pull-ups, IR-RX |

## 230-V-Lastgruppen (jede mit eigener Absicherung)

1. **LED-Netzteil 400 W** → geschaltet über Koppelrelais/Schütz an KC868 Y10.
   Sicherung nach NT-Datenblatt (Einschaltstrom beachten!).
2. **Abluft 230 V** → Koppelrelais/Schütz an KC868 Y11.
3. **Entfeuchter** → WLAN-Steckdose (nicht sicherheitskritisch, siehe safety).
4. **Luftbefeuchter Oraimo** → eigene 230-V-Zuleitung, per IR gesteuert.

## 12-V-Budget (grobe Abschätzung — real messen!)

| Verbraucher | Annahme | TODO |
|-------------|---------|------|
| Magnetventile 12 V | je ~0,5–1 A, i. d. R. 1 gleichzeitig | reale Spulendaten |
| Pumpe 12 V | je nach Typ 1–5 A | Datenblatt Pumpe |
| 2× Lüfter 12 V | je 0,1–0,3 A | Datenblatt Lüfter |
| Koppelrelais-Spulen | je ~30–70 mA | — |

12-V-Netzteil mit **Reserve** wählen (Summe größter gleichzeitiger Lasten
+ Einschaltspitzen). Getrennte Absicherung für Pumpe/Ventile empfehlenswert.

## Koppelrelais / Schütze

- 12-V-Spule vom KC868-MOSFET (Low-Side) geschaltet, **Freilaufdiode** an der
  Spule, falls das Relaismodul keine integrierte hat.
- Kontaktseite 230 V, ausreichend dimensioniert für die jeweilige Last
  (LED-NT-Einschaltstrom / Motoranlaufstrom der Abluft berücksichtigen).

## Not-Aus (hardwareseitig)

Ein Not-Aus soll die **gefährlichen Lasten hardwareseitig** trennen
(z. B. Schütz in der 230-V-Zuleitung von LED + Abluft + Pumpenkreis), nicht nur
softwareseitig über den ESP. PE niemals schalten.

## Kondensat / Schutzart

Feuchte Umgebung: Elektronik in Gehäuse mit geeigneter Schutzart, Kondensat
darf keine Elektronik erreichen; Kabel mit Abtropfschlaufe führen.
