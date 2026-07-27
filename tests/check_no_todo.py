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
# "TODO" alleine ebenfalls prüfen (Revisionen/MACs), aber separat melden.
# Ein nachgestellter Kommentar darf den Treffer nicht verstecken.
BARE_TODO = re.compile(r':\s*"?TODO"?\s*(?:#.*)?$')
# Gefährlich ist ein Marker NEBEN einem konkreten Pin — reine Fließtext-
# Kommentare ohne GPIO-Nummer sind Dokumentation und kein Risiko.
CONCRETE_PIN = re.compile(r"\bGPIO\s?\d{1,2}\b")


def scan_substitutions(path: pathlib.Path):
    """Trennt harte Pin-/Kalibrier-TODOs von weichen (Revision, MAC)."""
    hard, soft = [], []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip().startswith("#"):
            continue
        if any(tok in line for tok in TOKENS):
            hard.append((i, line.strip()))
        elif BARE_TODO.search(line):
            soft.append((i, line.strip()))
    return hard, soft


def scan_yaml_tree():
    """Sucht TODO-Marker in nodes/ und packages/.

    Wichtig auch in Kommentaren: dort steht der Marker typischerweise NEBEN
    einer plausibel aussehenden, aber ungeprüften GPIO-Nummer. Ein solcher Pin
    ist für `esphome config` gültig — dieser Scan ist dann die einzige Sperre.
    """
    findings = []
    for folder in ("nodes", "packages"):
        for path in sorted((ROOT / folder).glob("*.yaml")):
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if any(tok in line for tok in TOKENS) and CONCRETE_PIN.search(line):
                    findings.append((path.relative_to(ROOT), i, line.strip()))
    return findings


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

    hard, soft = scan_substitutions(path)
    yaml_hits = scan_yaml_tree()

    if hard:
        print(f"[GUARD] {path.name}: {len(hard)} PIN-/KALIBRIER-TODOs offen — "
              f"NICHT produktiv flashen:")
        for i, l in hard:
            print(f"  Zeile {i}: {l}")
    if yaml_hits:
        print(f"[GUARD] {len(yaml_hits)} ungeprüfte Pins direkt in der "
              f"Konfiguration — NICHT flashen:")
        for rel, i, l in yaml_hits:
            print(f"  {rel}:{i}: {l}")
    if soft:
        print(f"[GUARD] {path.name}: {len(soft)} Revisions-/MAC-TODOs offen:")
        for i, l in soft:
            print(f"  Zeile {i}: {l}")

    if hard or yaml_hits:
        return 1
    if soft:
        print("[GUARD] Warnung: nur unkritische TODOs — Compile möglich, "
              "Produktivbetrieb erst nach Klärung.")
        return 0
    print("[GUARD] OK — keine offenen TODOs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
