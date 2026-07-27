"""Tests des übergeordneten Zustandsautomaten und der Sicherheitsprioritäten."""
import pytest
from ghlib import (Mode, Setpoints, SensorState, supervise)

SP = Setpoints()


def good_sensor(t=25.0, rh=60.0, age=10.0):
    return SensorState(t_air=t, rh=rh, age_s=age, timeout_s=120.0)


def test_comm_fail_forces_emergency():
    a = supervise(Mode.AUTO_VPD, good_sensor(), SP, comm_ok=False)
    assert a.mode == Mode.EMERGENCY
    assert a.exhaust is True
    assert a.led_allowed is False
    assert a.humidifier is False
    assert a.irrigation_allowed is False
    assert a.alarm is True
    assert a.reason == "COMM_FAIL"


def test_sensor_fault_forces_safe_state():
    bad = SensorState(t_air=float("nan"), rh=60.0, age_s=5.0, timeout_s=120.0)
    a = supervise(Mode.AUTO_VPD, bad, SP)
    assert a.mode == Mode.EMERGENCY
    assert a.exhaust is True
    assert a.led_allowed is False
    assert a.humidifier is False
    assert a.dehumidifier is False
    assert a.irrigation_allowed is False
    assert a.reason == "SENSOR_FAULT"


def test_stale_sensor_is_fault():
    stale = SensorState(t_air=25.0, rh=60.0, age_s=500.0, timeout_s=120.0)
    a = supervise(Mode.AUTO_VPD, stale, SP)
    assert a.reason == "SENSOR_FAULT"


def test_overtemp_beats_vpd():
    a = supervise(Mode.AUTO_VPD, good_sensor(t=36.0, rh=30.0), SP)
    assert a.mode == Mode.EMERGENCY
    assert a.reason == "OVERTEMP"
    assert a.exhaust is True
    assert a.recirc_fan_pct == SP.fan_emergency
    assert a.led_allowed is False


def test_max_temp_turns_on_exhaust():
    a = supervise(Mode.AUTO_VPD, good_sensor(t=31.0, rh=40.0), SP)
    assert a.reason == "MAX_TEMP"
    assert a.exhaust is True
    assert a.humidifier is False


def test_min_temp_stops_cooling():
    a = supervise(Mode.AUTO_TEMPERATURE, good_sensor(t=17.0, rh=50.0), SP)
    assert a.reason == "MIN_TEMP"
    assert a.exhaust is False
    assert a.humidifier is False


def test_max_humidity_priority():
    # gültig, temperatur ok, aber RH über Limit
    a = supervise(Mode.AUTO_VPD, good_sensor(t=24.0, rh=85.0), SP)
    assert a.reason in ("CONDENSATION", "MAX_RH")
    assert a.dehumidifier is True
    assert a.humidifier is False


def test_vpd_low_dehumidifies():
    # feuchte Luft, moderate Temperatur -> VPD niedrig -> entfeuchten
    a = supervise(Mode.AUTO_VPD, good_sensor(t=24.0, rh=78.0), SP)
    # RH 78 < max_humidity 80, aber nahe -> kann Kondensation triggern; test auf entfeuchten
    assert a.dehumidifier is True
    assert a.humidifier is False


def test_vpd_high_humidifies():
    # trockene Luft -> VPD hoch -> befeuchten
    a = supervise(Mode.AUTO_VPD, good_sensor(t=25.0, rh=35.0), SP)
    assert a.reason == "VPD_HIGH"
    assert a.humidifier is True
    assert a.dehumidifier is False


def test_vpd_in_band_idle():
    sp = Setpoints(target_vpd=1.2, vpd_deadband=0.3, leaf_offset=0.0)
    # 25°C, RH so wählen dass VPD ~1.2
    a = supervise(Mode.AUTO_VPD, good_sensor(t=25.0, rh=62.0), sp)
    assert a.reason == "VPD_OK"
    assert a.humidifier is False
    assert a.dehumidifier is False


def test_off_mode():
    a = supervise(Mode.OFF, good_sensor(), SP)
    assert a.mode == Mode.OFF
    assert a.recirc_fan_pct == 0.0


def test_auto_temp_fan_ramp_monotonic():
    prev = -1.0
    for t in [25.0, 26.0, 27.0, 28.0, 29.0]:
        a = supervise(Mode.AUTO_TEMPERATURE, good_sensor(t=t, rh=45.0), SP)
        assert a.recirc_fan_pct >= prev
        prev = a.recirc_fan_pct
