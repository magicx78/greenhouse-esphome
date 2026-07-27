# Deploy auf den HA-Dev-Server (10.10.10.205, HAOS VM 101 auf Proxmox200)

Der Dev-Server läuft **Home Assistant OS** — dort gibt es keine native
Python-/venv-Umgebung. Der etablierte Weg ist deshalb **Weg A**.

## Weg A: HAOS mit ESPHome-Builder-Add-on + docker exec (Standard)

Quelle der Wahrheit ist GitHub (`magicx78/greenhouse-esphome`). Auf dem Server
liegt ein Klon unter `/config/esphome/greenhouse-esphome`.

**Einmalig einrichten:**

```bash
# per SSH (Terminal & SSH-Add-on, Profil "hadev"):
git clone https://github.com/magicx78/greenhouse-esphome /config/esphome/greenhouse-esphome
cp /config/esphome/greenhouse-esphome/deploy/haos-wrappers/*.yaml /config/esphome/
# secrets.yaml + substitutions.yaml im Projekt-Root anlegen (aus den *.example.yaml,
# echte Werte eintragen — bleiben un-committet)
```

**Voraussetzung für die CLI:** Beim Terminal & SSH-Add-on den **Protection Mode
ausschalten** (Einstellungen → Add-ons → Terminal & SSH), sonst gibt es kein
`docker`. Der Builder-Container heißt hier `addon_5c53de3b_esphome-dev`
(ESPHome Device Builder **dev**-Channel; bei anderem Add-on `docker ps | grep esphome`).

**Update + Validieren + Kompilieren:**

```bash
git -C /config/esphome/greenhouse-esphome pull
docker exec addon_5c53de3b_esphome-dev esphome config  /config/esphome/greenhouse-esphome/nodes/kc868-a16.yaml
docker exec addon_5c53de3b_esphome-dev esphome compile /config/esphome/greenhouse-esphome/nodes/kc868-a16.yaml
```

Alternativ ohne CLI: ESPHome-Builder-Dashboard (HA-UI → Add-on → Web-UI) — die
Wrapper aus `deploy/haos-wrappers/` erscheinen dort als drei Nodes mit
**Validate**/**Install**-Buttons.

**Änderungs-Workflow:** Nie direkt im Server-Klon editieren. Änderungen lokal
(Scratchpad-Klon) → `pytest` grün → push → auf dem Server `git pull`.

## Weg B: CLI in venv (generische Linux-VM/LXC mit Python ≥3.10, NICHT HAOS)

```bash
git clone https://github.com/magicx78/greenhouse-esphome && cd greenhouse-esphome
bash deploy/install-dev-server.sh
```

Das Skript richtet die venv ein, installiert ESPHome, führt die pytest-Suite
und den Build-Guard aus und validiert alle drei Knoten (`kc868-a16` muss OK
sein; `greenhouse-io`/`greenhouse-hmi` sind absichtlich blockiert, bis die
Pin-TODOs in `substitutions.yaml` ausgefüllt sind).

## Erwartetes Ergebnis der Erst-Validierung

| Knoten | Erwartung |
|--------|-----------|
| `kc868-a16` | ✅ CONFIG OK (alle Pins bestätigt) |
| `greenhouse-io` | ⛔ blockiert bis `*_pin`-TODOs gesetzt |
| `greenhouse-hmi` | ⛔ blockiert bis RS485-/Touch-Pins der Board-Revision gesetzt |

## Flashen (Reihenfolge)

1. `kc868-a16`: 433-MHz-Module abziehen, USB-C verbinden, **S2 halten** und 12 V
   anlegen → `esphome run nodes/kc868-a16.yaml`
2. `greenhouse-io`: normales USB-Flashen des DevKits.
3. `greenhouse-hmi`: USB-C, ggf. BOOT-Taste beim ersten Flash.

Danach: Inbetriebnahmeplan `docs/commissioning.md`, Phase 1–11.
