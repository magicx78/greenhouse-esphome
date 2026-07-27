# Deploy auf den HA-Dev-Server (10.10.10.205, HAOS VM 101 auf Proxmox200)

Der Dev-Server läuft **Home Assistant OS** — dort gibt es keine native
Python-/venv-Umgebung. Der etablierte Weg ist deshalb **Weg A**.

## Weg A: HAOS mit ESPHome-Builder-Add-on + docker exec (Standard)

Quelle der Wahrheit ist GitHub (`magicx78/greenhouse-esphome`). Auf dem Server
liegt ein Klon unter `/config/esphome/greenhouse-esphome`.

**Einmalig einrichten:**

```bash
# per SSH (Add-on "Advanced SSH & Web Terminal", Profil "hadev", User test + Key):
sudo git clone https://github.com/magicx78/greenhouse-esphome /config/esphome/greenhouse-esphome
sudo cp /config/esphome/greenhouse-esphome/deploy/haos-wrappers/*.yaml /config/esphome/
# secrets.yaml + substitutions.yaml im Projekt-Root anlegen (aus den *.example.yaml,
# echte Werte eintragen — bleiben un-committet)
```

**Voraussetzung für die CLI:** Beim SSH-Add-on den **Protection Mode ausschalten**
(Einstellungen → Apps → Advanced SSH & Web Terminal → Info), sonst gibt es kein
`docker`. Die SSH-Session läuft als User `test` (uid 1000) → Docker/Git immer mit
`sudo` (passwortlos). Der Builder-Container heißt hier `addon_5c53de3b_esphome-dev`
(ESPHome Device Builder **dev**-Channel; bei anderem Add-on `docker ps | grep esphome`).

**Update + Validieren + Kompilieren:**

```bash
sudo git -C /config/esphome/greenhouse-esphome pull
sudo docker exec addon_5c53de3b_esphome-dev esphome config  /config/esphome/greenhouse-esphome/nodes/kc868-a16.yaml
sudo docker exec addon_5c53de3b_esphome-dev esphome compile /config/esphome/greenhouse-esphome/nodes/kc868-a16.yaml
```

**Netzwerkmodus des KC868:** `network_mode` im `substitutions:`-Block von
`nodes/kc868-a16.yaml` — `wifi` (aktuell) oder `ethernet` (LAN8720, Zielzustand).
Der Wert muss dort stehen, weil er einen `!include`-Dateinamen bildet; in
`substitutions.yaml` wäre er zu spät aufgelöst.

> ⚠️ **Wrapper-Weg (`deploy/haos-wrappers/`) funktioniert für `kc868-a16` nicht:**
> ESPHome löst den relativen Pfad aus `esphome: includes:`
> (`../components/greenhouse_controller/vpd_math.h`) gegen die **Wrapper**-Datei
> statt gegen die Node-Datei auf → „Could not find file". Für diesen Knoten
> deshalb den CLI-Weg oben benutzen. Die Wrapper der beiden anderen Knoten sind
> davon nicht betroffen (sie binden keine C++-Header ein).

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
