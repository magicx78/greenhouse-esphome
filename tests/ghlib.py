"""
ghlib.py — Pure-Python-Referenzimplementierung der sicherheitskritischen
Gewächshaus-Logik.

Diese Datei ist die *ausführbare Spezifikation*. Die C++ External Component
(components/greenhouse_controller) MUSS sich exakt gleich verhalten. Alle
Formeln und Zustandsübergänge werden von tests/test_*.py verifiziert.

Keine ESPHome-Abhängigkeiten -> lässt sich mit reinem pytest testen.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import IntEnum

NAN = float("nan")


# ---------------------------------------------------------------------------
# 1) Psychrometrie / VPD
# ---------------------------------------------------------------------------

def svp_kpa(t_c: float) -> float:
    """Sättigungsdampfdruck in kPa (Tetens/FAO-56)."""
    return 0.6108 * math.exp((17.27 * t_c) / (t_c + 237.3))


def vpd_air_kpa(t_c: float, rh: float) -> float:
    """Luft-VPD (kPa). rh in %."""
    return svp_kpa(t_c) * (1.0 - rh / 100.0)


def vpd_leaf_kpa(t_air_c: float, rh: float, leaf_offset_c: float) -> float:
    """Geschätzter Blatt-VPD (kPa). Blatt meist kühler -> Offset typ. negativ.

    VPD_leaf = SVP(T_leaf) - RH/100 * SVP(T_air)
    """
    t_leaf = t_air_c + leaf_offset_c
    return svp_kpa(t_leaf) - (rh / 100.0) * svp_kpa(t_air_c)


def dew_point_c(t_c: float, rh: float) -> float:
    """Taupunkt (°C), Magnus-Näherung. rh in % (>0)."""
    rh = max(rh, 1e-3)
    alpha = math.log(rh / 100.0) + (17.27 * t_c) / (237.3 + t_c)
    return (237.3 * alpha) / (17.27 - alpha)


def abs_humidity_g_m3(t_c: float, rh: float) -> float:
    """Absolute Luftfeuchte (g/m³), Magnus-basiert (243.12/17.62)."""
    svp_hpa = 6.112 * math.exp((17.62 * t_c) / (243.12 + t_c))
    return 216.7 * (rh / 100.0 * svp_hpa) / (273.15 + t_c)


# ---------------------------------------------------------------------------
# 2) Sensor-Plausibilität
# ---------------------------------------------------------------------------

TEMP_MIN, TEMP_MAX = -20.0, 70.0
RH_MIN, RH_MAX = 0.0, 100.0


def temp_valid(t) -> bool:
    return t is not None and not math.isnan(t) and TEMP_MIN <= t <= TEMP_MAX


def rh_valid(rh) -> bool:
    return rh is not None and not math.isnan(rh) and RH_MIN <= rh <= RH_MAX


def sensor_fresh(age_s: float, timeout_s: float) -> bool:
    return age_s is not None and not math.isnan(age_s) and age_s <= timeout_s


# ---------------------------------------------------------------------------
# 3) Modbus-Registerplan
# ---------------------------------------------------------------------------

# (name, wortbreite, writable) je Startadresse
REGISTER_MAP = {
    0x0000: ("protocol_version",        1, False),
    0x0001: ("firmware_version",        1, False),
    0x0002: ("server_uptime_s",         2, False),   # belegt 0x0002-0x0003
    0x0004: ("last_master_heartbeat",   1, True),    # Master schreibt Zähler
    0x0005: ("comm_status",             1, False),
    0x0006: ("error_bitmask",           1, False),

    0x0010: ("requested_output_mask",   1, True),
    0x0011: ("active_output_mask",      1, False),
    0x0012: ("allowed_output_mask",     1, True),
    0x0013: ("locked_output_mask",      1, False),

    0x0020: ("command_sequence",        1, True),
    0x0021: ("acked_sequence",          1, False),
    0x0022: ("watchdog_time_s",         1, True),
    0x0023: ("operating_mode",          1, True),

    0x0030: ("valve_max_time_s",        1, True),
    0x0031: ("pump_post_run_s",         1, True),
    0x0032: ("pump_pre_run_s",          1, True),
    0x0033: ("max_active_valves",       1, True),
}

# Output-Bitbelegung
BIT_VALVE_1 = 0
BIT_VALVE_8 = 7
BIT_PUMP = 8
BIT_LED = 9
BIT_EXHAUST = 10
RESERVE_BITS = (11, 12, 13, 14, 15)
VALVE_BITS = tuple(range(BIT_VALVE_1, BIT_VALVE_8 + 1))


def register_overlaps() -> list:
    """Liefert Liste von Adress-Kollisionen (soll leer sein)."""
    used = {}
    collisions = []
    for start, (name, words, _w) in REGISTER_MAP.items():
        for a in range(start, start + words):
            if a in used:
                collisions.append((a, used[a], name))
            else:
                used[a] = name
    return collisions


# ---------------------------------------------------------------------------
# 4) Ausgangs-Arbitrierung (läuft logisch auf dem KC868-A16)
# ---------------------------------------------------------------------------

def bit(mask: int, n: int) -> bool:
    return bool(mask >> n & 1)


def arbitrate_outputs(requested: int, allowed: int, locked: int,
                      watchdog_ok: bool, max_active_valves: int = 1,
                      exhaust_failsafe: bool = True) -> int:
    """Bestimmt die logisch aktive Ausgangsbitmaske.

    Regeln:
    - Bei Watchdog-Ausfall: alle gefährlichen Ausgänge AUS, Abluft EIN (Failsafe).
    - Effektiv = requested & allowed & ~locked.
    - Pumpe nur, wenn mindestens ein Ventil offen ist (Trockenlauf-Interlock).
    - Max. gleichzeitig offene Ventile begrenzen (niedrigste Bits gewinnen).
    """
    if not watchdog_ok:
        return 1 << BIT_EXHAUST if exhaust_failsafe else 0

    eff = requested & allowed & ~locked & 0xFFFF

    # Ventil-Limit
    open_valves = [b for b in VALVE_BITS if bit(eff, b)]
    if len(open_valves) > max_active_valves:
        keep = set(open_valves[:max_active_valves])
        for b in open_valves:
            if b not in keep:
                eff &= ~(1 << b)

    # Pumpen-Interlock: Pumpe nur mit offenem Ventil
    any_valve = any(bit(eff, b) for b in VALVE_BITS)
    if bit(eff, BIT_PUMP) and not any_valve:
        eff &= ~(1 << BIT_PUMP)

    return eff & 0xFFFF


def boot_output_mask(exhaust_on: bool = True) -> int:
    """Sicherer Bootzustand: alles AUS, Abluft optional EIN."""
    return 1 << BIT_EXHAUST if exhaust_on else 0


def command_accepted(seq_new: int, seq_last: int, watchdog_ok: bool,
                     registers_valid: bool, locally_blocked: bool) -> bool:
    """Ein Ausgangsbefehl wird nur unter allen Bedingungen akzeptiert."""
    return (registers_valid and watchdog_ok and not locally_blocked
            and seq_new != seq_last)


# ---------------------------------------------------------------------------
# 5) Übergeordneter Zustandsautomat (läuft logisch auf dem HMI-Supervisor)
# ---------------------------------------------------------------------------

class Mode(IntEnum):
    OFF = 0
    MANUAL = 1
    AUTO_TEMPERATURE = 2
    AUTO_VPD = 3
    IRRIGATION = 4
    EMERGENCY = 5
    MAINTENANCE = 6


@dataclass
class Setpoints:
    target_temp: float = 25.0
    min_temp: float = 18.0
    max_temp: float = 30.0
    emergency_temp: float = 35.0
    target_vpd: float = 1.0
    vpd_deadband: float = 0.1
    leaf_offset: float = -1.0
    fan_min: float = 25.0
    fan_max: float = 100.0
    fan_emergency: float = 100.0
    max_humidity: float = 80.0


@dataclass
class SensorState:
    t_air: float = NAN
    rh: float = NAN
    age_s: float = 0.0
    timeout_s: float = 120.0

    @property
    def valid(self) -> bool:
        return (temp_valid(self.t_air) and rh_valid(self.rh)
                and sensor_fresh(self.age_s, self.timeout_s))


@dataclass
class Actions:
    mode: Mode = Mode.OFF
    led_allowed: bool = False
    humidifier: bool = False
    dehumidifier: bool = False
    exhaust: bool = False
    recirc_fan_pct: float = 0.0
    irrigation_allowed: bool = False
    alarm: bool = False
    reason: str = ""


def supervise(requested_mode: Mode, s: SensorState, sp: Setpoints,
              comm_ok: bool = True) -> Actions:
    """Prioritätsbasierter Zustandsautomat. Gibt die Sollaktionen zurück.

    Prioritäten (höchste zuerst):
      1 el./therm. Sicherheit (comm/Watchdog)
      2 Sensorfehler
      3 Maximaltemperatur
      4 Minimaltemperatur
      5 Kondensationsschutz
      6 Maximale Luftfeuchte
      7 VPD-Regelung
      8 Komfort/Energie
    """
    a = Actions(mode=requested_mode)

    # Prio 1: Kommunikations-/Sicherheitsausfall
    if not comm_ok:
        return Actions(mode=Mode.EMERGENCY, led_allowed=False, humidifier=False,
                       dehumidifier=False, exhaust=True,
                       recirc_fan_pct=sp.fan_min, irrigation_allowed=False,
                       alarm=True, reason="COMM_FAIL")

    if requested_mode in (Mode.OFF, Mode.MAINTENANCE):
        return Actions(mode=requested_mode, exhaust=(requested_mode == Mode.OFF),
                       recirc_fan_pct=0.0, reason=requested_mode.name)

    # Prio 2: Sensorfehler des Gewächshaussensors -> sicherer Rückfall
    if not s.valid:
        return Actions(mode=Mode.EMERGENCY, led_allowed=False, humidifier=False,
                       dehumidifier=False, exhaust=True,
                       recirc_fan_pct=sp.fan_min, irrigation_allowed=False,
                       alarm=True, reason="SENSOR_FAULT")

    # Ab hier: Sensor gültig.
    a.led_allowed = True
    a.recirc_fan_pct = sp.fan_min
    a.irrigation_allowed = requested_mode in (Mode.AUTO_TEMPERATURE,
                                              Mode.AUTO_VPD, Mode.IRRIGATION,
                                              Mode.MANUAL)

    # Prio 3: Übertemperatur / Notfall
    if s.t_air >= sp.emergency_temp:
        a.mode = Mode.EMERGENCY
        a.exhaust = True
        a.recirc_fan_pct = sp.fan_emergency
        a.humidifier = False
        a.dehumidifier = False
        a.led_allowed = False   # LED als Wärmequelle abschalten
        a.irrigation_allowed = False
        a.alarm = True
        a.reason = "OVERTEMP"
        return a

    if s.t_air >= sp.max_temp:
        a.exhaust = True
        a.recirc_fan_pct = max(sp.fan_min, min(sp.fan_max, sp.fan_max))
        a.humidifier = False
        a.reason = "MAX_TEMP"
        return a

    # Prio 4: Untertemperatur
    if s.t_air <= sp.min_temp:
        a.exhaust = False
        a.recirc_fan_pct = sp.fan_min
        a.humidifier = False
        a.reason = "MIN_TEMP"
        return a

    # Prio 5: Kondensationsschutz (nahe Taupunkt)
    if (s.t_air - dew_point_c(s.t_air, s.rh)) < 1.5:
        a.exhaust = True
        a.recirc_fan_pct = max(sp.fan_min, 50.0)
        a.humidifier = False
        a.dehumidifier = True
        a.reason = "CONDENSATION"
        return a

    # Prio 6: Maximale Luftfeuchte
    if s.rh >= sp.max_humidity:
        a.exhaust = True
        a.dehumidifier = True
        a.humidifier = False
        a.recirc_fan_pct = max(sp.fan_min, 50.0)
        a.reason = "MAX_RH"
        return a

    # Prio 7: VPD-Regelung
    if requested_mode == Mode.AUTO_VPD:
        vpd = vpd_leaf_kpa(s.t_air, s.rh, sp.leaf_offset)
        low = sp.target_vpd - sp.vpd_deadband
        high = sp.target_vpd + sp.vpd_deadband
        if vpd < low:            # Luft zu feucht
            a.humidifier = False
            a.dehumidifier = True
            a.recirc_fan_pct = max(sp.fan_min, 50.0)
            a.reason = "VPD_LOW"
        elif vpd > high:         # Luft zu trocken
            a.dehumidifier = False
            a.humidifier = True
            a.recirc_fan_pct = sp.fan_min
            a.reason = "VPD_HIGH"
        else:
            a.reason = "VPD_OK"
        return a

    # Prio 7b: reine Temperaturregelung
    if requested_mode == Mode.AUTO_TEMPERATURE:
        span = max(0.1, sp.max_temp - sp.target_temp)
        over = max(0.0, s.t_air - sp.target_temp)
        frac = min(1.0, over / span)
        a.recirc_fan_pct = sp.fan_min + frac * (sp.fan_max - sp.fan_min)
        a.exhaust = s.t_air >= (sp.target_temp + span * 0.5)
        a.reason = "AUTO_TEMP"
        return a

    a.reason = requested_mode.name
    return a
