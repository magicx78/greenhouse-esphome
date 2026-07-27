"""Tests der Psychrometrie/VPD-Formeln und Sensor-Plausibilität."""
import math
import pytest
from ghlib import (svp_kpa, vpd_air_kpa, vpd_leaf_kpa, dew_point_c,
                   abs_humidity_g_m3, temp_valid, rh_valid, sensor_fresh)


def test_svp_known_points():
    # SVP(20°C) ~ 2.338 kPa (FAO-56)
    assert svp_kpa(20.0) == pytest.approx(2.338, abs=0.01)
    # SVP(0°C) ~ 0.6108 kPa
    assert svp_kpa(0.0) == pytest.approx(0.6108, abs=0.001)
    # SVP(25°C) ~ 3.168 kPa
    assert svp_kpa(25.0) == pytest.approx(3.168, abs=0.01)


def test_svp_monotonic():
    prev = -1.0
    for t in range(-10, 45):
        v = svp_kpa(t)
        assert v > prev
        prev = v


def test_vpd_air_bounds():
    # 100% RH -> VPD 0
    assert vpd_air_kpa(25.0, 100.0) == pytest.approx(0.0, abs=1e-9)
    # 0% RH -> VPD = SVP
    assert vpd_air_kpa(25.0, 0.0) == pytest.approx(svp_kpa(25.0), abs=1e-9)
    # bei 50% RH die Hälfte von SVP
    assert vpd_air_kpa(25.0, 50.0) == pytest.approx(svp_kpa(25.0) * 0.5, abs=1e-9)


def test_vpd_air_typical_range():
    # 26°C / 60% RH -> ~1.34 kPa
    assert vpd_air_kpa(26.0, 60.0) == pytest.approx(1.343, abs=0.02)


def test_vpd_leaf_offset_effect():
    # Kühleres Blatt (negativer Offset) senkt den VPD gegenüber offset=0
    base = vpd_leaf_kpa(25.0, 60.0, 0.0)
    cooler = vpd_leaf_kpa(25.0, 60.0, -2.0)
    assert cooler < base
    # bei offset 0 entspricht Blatt-VPD dem Luft-VPD
    assert vpd_leaf_kpa(25.0, 60.0, 0.0) == pytest.approx(vpd_air_kpa(25.0, 60.0), abs=1e-9)


def test_dew_point():
    # 25°C / 100% -> Taupunkt ~ Temperatur
    assert dew_point_c(25.0, 100.0) == pytest.approx(25.0, abs=0.2)
    # 25°C / 50% -> ~13.9°C
    assert dew_point_c(25.0, 50.0) == pytest.approx(13.9, abs=0.4)
    # Taupunkt immer <= Lufttemperatur
    for t in (10, 20, 30):
        for rh in (20, 50, 90):
            assert dew_point_c(t, rh) <= t + 1e-6


def test_abs_humidity():
    # 20°C / 50% -> ~8.6 g/m³
    assert abs_humidity_g_m3(20.0, 50.0) == pytest.approx(8.6, abs=0.3)
    # steigt mit RH
    assert abs_humidity_g_m3(20.0, 80.0) > abs_humidity_g_m3(20.0, 40.0)


def test_sensor_validity():
    assert temp_valid(25.0)
    assert not temp_valid(float("nan"))
    assert not temp_valid(999.0)
    assert not temp_valid(-50.0)
    assert rh_valid(55.0)
    assert not rh_valid(float("nan"))
    assert not rh_valid(150.0)
    assert not rh_valid(-1.0)


def test_sensor_freshness():
    assert sensor_fresh(30.0, 120.0)
    assert not sensor_fresh(200.0, 120.0)
    assert not sensor_fresh(float("nan"), 120.0)
