"""Tests des Modbus-Registerplans und der Ausgangs-Arbitrierung/Interlocks."""
import pytest
from ghlib import (REGISTER_MAP, register_overlaps, arbitrate_outputs,
                   boot_output_mask, command_accepted, bit,
                   BIT_PUMP, BIT_LED, BIT_EXHAUST, VALVE_BITS)


def test_no_register_overlaps():
    assert register_overlaps() == []


def test_uptime_is_two_words():
    assert REGISTER_MAP[0x0002][1] == 2  # U_DWORD


def test_writable_flags_present():
    # angeforderte Ausgänge sind beschreibbar, aktive nicht
    assert REGISTER_MAP[0x0010][2] is True   # requested
    assert REGISTER_MAP[0x0011][2] is False  # active
    assert REGISTER_MAP[0x0012][2] is True   # allowed
    assert REGISTER_MAP[0x0013][2] is False  # locked


def test_boot_state_safe():
    m = boot_output_mask(exhaust_on=True)
    assert bit(m, BIT_EXHAUST) is True
    assert bit(m, BIT_PUMP) is False
    assert bit(m, BIT_LED) is False
    for b in VALVE_BITS:
        assert bit(m, b) is False


def test_watchdog_fail_failsafe():
    # alles angefordert, aber Watchdog aus -> nur Abluft
    m = arbitrate_outputs(requested=0xFFFF, allowed=0xFFFF, locked=0x0000,
                          watchdog_ok=False)
    assert m == (1 << BIT_EXHAUST)


def test_pump_requires_open_valve():
    # Pumpe (bit8) angefordert, aber kein Ventil -> Pumpe gesperrt
    m = arbitrate_outputs(requested=(1 << BIT_PUMP), allowed=0xFFFF,
                          locked=0x0000, watchdog_ok=True)
    assert bit(m, BIT_PUMP) is False


def test_pump_allowed_with_valve():
    req = (1 << BIT_PUMP) | (1 << 0)  # Pumpe + Ventil 1
    m = arbitrate_outputs(requested=req, allowed=0xFFFF, locked=0x0000,
                          watchdog_ok=True, max_active_valves=1)
    assert bit(m, BIT_PUMP) is True
    assert bit(m, 0) is True


def test_max_one_valve_default():
    req = 0b1111  # Ventil 1..4
    m = arbitrate_outputs(requested=req, allowed=0xFFFF, locked=0x0000,
                          watchdog_ok=True, max_active_valves=1)
    open_valves = [b for b in VALVE_BITS if bit(m, b)]
    assert len(open_valves) == 1
    assert open_valves[0] == 0  # niedrigstes Bit gewinnt


def test_locked_output_removed():
    req = (1 << BIT_LED)
    m = arbitrate_outputs(requested=req, allowed=0xFFFF, locked=(1 << BIT_LED),
                          watchdog_ok=True)
    assert bit(m, BIT_LED) is False


def test_allowed_mask_gates():
    req = (1 << BIT_LED)
    m = arbitrate_outputs(requested=req, allowed=0x0000, locked=0x0000,
                          watchdog_ok=True)
    assert m == 0


def test_command_acceptance():
    assert command_accepted(5, 4, watchdog_ok=True, registers_valid=True,
                            locally_blocked=False) is True
    # gleiche Sequenz -> abgelehnt
    assert command_accepted(4, 4, True, True, False) is False
    # Watchdog aus -> abgelehnt
    assert command_accepted(5, 4, False, True, False) is False
    # lokale Sperre -> abgelehnt
    assert command_accepted(5, 4, True, True, True) is False
