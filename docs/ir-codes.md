# IR-Codes Oraimo OHM-H01 (ir-codes.md)

> **Keine IR-Codes erfinden.** Diese Tabelle wird beim Lernen (Phase 7) befüllt.
> Bis dahin sind alle Codes `TODO_LEARN`.

## Lernvorgang

1. `greenhouse-io` in den Lernmodus versetzen (Button „IR lernen").
2. Fernbedienungstaste drücken; `remote_receiver` loggt Protokoll/Adresse/
   Kommando (oder Raw-Timing, falls unbekanntes Protokoll).
3. Mehrere Wiederholungen vergleichen → stabile Sequenz.
4. Hier eintragen und in `packages/climate-control.yaml` (bzw. eigenes
   IR-Package auf greenhouse-io) als `remote_transmitter`-Aktion hinterlegen.

## Befehlstabelle (zu befüllen)

| Befehl | Protokoll | Adresse | Kommando | Raw (falls nötig) | Status |
|--------|-----------|---------|----------|-------------------|--------|
| Power | ? | ? | ? | ? | TODO_LEARN |
| Nebel niedrig | ? | ? | ? | ? | TODO_LEARN |
| Nebel mittel | ? | ? | ? | ? | TODO_LEARN |
| Nebel hoch | ? | ? | ? | ? | TODO_LEARN |
| Warmnebel (falls vorhanden) | ? | ? | ? | ? | TODO_LEARN |
| Kaltnebel | ? | ? | ? | ? | TODO_LEARN |
| Timer AUS | ? | ? | ? | ? | TODO_LEARN |

## Zustandsführung (Assumed State)

Der Luftbefeuchter liefert **keine** Rückmeldung → nur geschätzter Zustand
(`assumed state`). Bevorzugt absolute Befehle (Power On / Mist Level N). Falls
nur Toggle verfügbar:
- Shadow-State führen, Neustartzustand = **unbekannt**.
- Sichere Synchronisationssequenz dokumentieren (z. B. definierte Anzahl
  Toggles, um in bekannten Zustand zu kommen).
- Keine endlosen Toggle-Wiederholungen; Mindestzeit zwischen Befehlen;
  max. Anzahl Wiederholungen.
- Regelung zeitproportional (lange Fenster + Hysterese).
