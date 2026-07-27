#!/usr/bin/env python3
"""Build-Guard: verhindert produktives Flashen mit offenen Pin-/Kalibrier-TODOs.

Scannt substitutions.yaml (bzw. substitutions.example.yaml) nach den Tokens
TODO_AFTER_PIN_AUDIT / TODO_CALIBRATE / "TODO". Exit-Code != 0, wenn welche
gefunden werden. In CI vor `esphome compile` einhängen.

Zusätzlich ist der Schutz doppelt: ungültige Pin-Platzhalter lassen bereits
`esphome config` fehlschlagen.
"""
import sys
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
CANDIDATES = ["substitutions.yaml", "substitutions.example.yaml"]

TOKENS = ("TODO_AFTER_PIN_AUDIT", "TODO_CALIBRATE")
# "TODO" alleine ebenfalls prüfen (Revisionen/MACs), aber separat melden
BARE_TODO = re.compile(r':\s*"?TODO"?\s*$')


def main() -> int:
    path = None
    for c in CANDIDATES:
        p = ROOT / c
        if p.exists():
            path = p
            break
    if path is None:
        print("Keine substitutions-Datei gefunden.")
        return 2

    text = path.read_text(encoding="utf-8")
    hard = []
    soft = []
    for i, line in enumerate(text.splitlines(), 1):
        if line.strip().startswith("#"):
            continue
        if any(tok in line for tok in TOKENS):
            hard.append((i, line.strip()))
        elif BARE_TODO.search(line):
            soft.append((i, line.strip()))

    if hard:
        print(f"[GUARD] {path.name}: {len(hard)} PIN-/KALIBRIER-TODOs offen — "
              f"NICHT produktiv flashen:")
        for i, l in hard:
            print(f"  Zeile {i}: {l}")
    if soft:
        print(f"[GUARD] {path.name}: {len(soft)} Revisions-/MAC-TODOs offen:")
        for i, l in soft:
            print(f"  Zeile {i}: {l}")

    if hard:
        return 1
    if soft:
        print("[GUARD] Warnung: nur unkritische TODOs — Compile möglich, "
              "Produktivbetrieb erst nach Klärung.")
        return 0
    print("[GUARD] OK — keine offenen TODOs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
