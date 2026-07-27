#!/usr/bin/env bash
# install-dev-server.sh — Bootstrap für eine generische Linux-VM/LXC (Weg B).
# NICHT für HAOS: dort läuft der Builder-Add-on-Weg (siehe README-deploy.md, Weg A).
# Richtet eine Python-venv mit ESPHome ein, legt secrets/substitutions an und
# validiert die Knoten. Aufruf im Projekt-Root (greenhouse-esphome/):
#   bash deploy/install-dev-server.sh
set -euo pipefail

cd "$(dirname "$0")/.."
echo "== greenhouse-esphome Bootstrap =="

# 1) Python-venv + ESPHome
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
pip install esphome pytest -q
echo "ESPHome: $(esphome version)"

# 2) Konfig-Dateien anlegen (falls fehlend)
[ -f secrets.yaml ] || { cp secrets.example.yaml secrets.yaml; echo ">> secrets.yaml angelegt — BITTE AUSFÜLLEN"; }
[ -f substitutions.yaml ] || { cp substitutions.example.yaml substitutions.yaml; echo ">> substitutions.yaml angelegt — TODOs AUSFÜLLEN"; }

# 3) Kernlogik-Tests
echo "== pytest =="
python3 -m pytest tests/ -q

# 4) Build-Guard (warnt/blockt bei offenen Pin-TODOs)
echo "== Build-Guard =="
python3 tests/check_no_todo.py || true

# 5) Schema-Validierung — KC868 zuerst (alle Pins bestätigt)
echo "== esphome config: kc868-a16 =="
esphome config nodes/kc868-a16.yaml >/dev/null && echo "kc868-a16: CONFIG OK" \
  || echo "kc868-a16: CONFIG-FEHLER (Ausgabe oben prüfen)"

echo "== esphome config: greenhouse-io (erwartet FEHLER solange Pin-TODOs offen) =="
esphome config nodes/greenhouse-io.yaml >/dev/null && echo "greenhouse-io: CONFIG OK" \
  || echo "greenhouse-io: erwartungsgemäß blockiert (TODO_AFTER_PIN_AUDIT)"

echo "== esphome config: greenhouse-hmi (erwartet FEHLER solange Pin-TODOs offen) =="
esphome config nodes/greenhouse-hmi.yaml >/dev/null && echo "greenhouse-hmi: CONFIG OK" \
  || echo "greenhouse-hmi: erwartungsgemäß blockiert (TODO_AFTER_PIN_AUDIT)"

cat <<'EOF'

Nächste Schritte:
  1. secrets.yaml + substitutions.yaml ausfüllen (Pins nach Pin-Audit).
  2. esphome compile nodes/kc868-a16.yaml
  3. esphome compile nodes/greenhouse-io.yaml
  4. esphome compile nodes/greenhouse-hmi.yaml   (dauert beim ersten Mal lange: IDF-Toolchain + LVGL)
  5. Flashen per USB: esphome run nodes/<node>.yaml --device /dev/ttyUSB0
EOF
