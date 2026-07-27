#pragma once
// vpd_math.h — reine, ESPHome-unabhängige Psychrometrie- und Arbitrierungs-
// funktionen. 1:1-Spiegel von tests/ghlib.py (dort mit pytest verifiziert).
// Header-only, damit sowohl die External Component als auch YAML-`includes:`
// darauf zugreifen können.

#include <cmath>
#include <cstdint>

namespace greenhouse {

// ---- Output-Bitbelegung (identisch zu ghlib.py) -------------------------
static constexpr uint8_t BIT_VALVE_1 = 0;
static constexpr uint8_t BIT_VALVE_8 = 7;
static constexpr uint8_t BIT_PUMP = 8;
static constexpr uint8_t BIT_LED = 9;
static constexpr uint8_t BIT_EXHAUST = 10;

// ---- Psychrometrie ------------------------------------------------------
inline float svp_kpa(float t_c) {
  return 0.6108f * std::exp((17.27f * t_c) / (t_c + 237.3f));
}

inline float vpd_air_kpa(float t_c, float rh) {
  return svp_kpa(t_c) * (1.0f - rh / 100.0f);
}

inline float vpd_leaf_kpa(float t_air_c, float rh, float leaf_offset_c) {
  const float t_leaf = t_air_c + leaf_offset_c;
  return svp_kpa(t_leaf) - (rh / 100.0f) * svp_kpa(t_air_c);
}

inline float dew_point_c(float t_c, float rh) {
  if (rh < 1e-3f) rh = 1e-3f;
  const float alpha = std::log(rh / 100.0f) + (17.27f * t_c) / (237.3f + t_c);
  return (237.3f * alpha) / (17.27f - alpha);
}

inline float abs_humidity_g_m3(float t_c, float rh) {
  const float svp_hpa = 6.112f * std::exp((17.62f * t_c) / (243.12f + t_c));
  return 216.7f * (rh / 100.0f * svp_hpa) / (273.15f + t_c);
}

// ---- Plausibilität ------------------------------------------------------
inline bool temp_valid(float t) {
  return !std::isnan(t) && t >= -20.0f && t <= 70.0f;
}
inline bool rh_valid(float rh) {
  return !std::isnan(rh) && rh >= 0.0f && rh <= 100.0f;
}
inline bool sensor_fresh(float age_s, float timeout_s) {
  return !std::isnan(age_s) && age_s <= timeout_s;
}

// ---- Ausgangs-Arbitrierung (läuft auf dem KC868-A16) --------------------
inline bool bit_set(uint16_t mask, uint8_t n) { return (mask >> n) & 1u; }

inline uint16_t arbitrate_outputs(uint16_t requested, uint16_t allowed,
                                  uint16_t locked, bool watchdog_ok,
                                  uint8_t max_active_valves = 1,
                                  bool exhaust_failsafe = true) {
  if (!watchdog_ok)
    return exhaust_failsafe ? (uint16_t)(1u << BIT_EXHAUST) : 0u;

  uint16_t eff = requested & allowed & (uint16_t)~locked;

  // Ventil-Limit (niedrigste Bits gewinnen)
  uint8_t open_count = 0;
  for (uint8_t b = BIT_VALVE_1; b <= BIT_VALVE_8; b++) {
    if (bit_set(eff, b)) {
      open_count++;
      if (open_count > max_active_valves) eff &= (uint16_t)~(1u << b);
    }
  }

  // Pumpen-Interlock: Pumpe nur mit offenem Ventil
  bool any_valve = false;
  for (uint8_t b = BIT_VALVE_1; b <= BIT_VALVE_8; b++)
    if (bit_set(eff, b)) { any_valve = true; break; }
  if (bit_set(eff, BIT_PUMP) && !any_valve) eff &= (uint16_t)~(1u << BIT_PUMP);

  return eff;
}

inline uint16_t boot_output_mask(bool exhaust_on = true) {
  return exhaust_on ? (uint16_t)(1u << BIT_EXHAUST) : 0u;
}

inline bool command_accepted(uint16_t seq_new, uint16_t seq_last,
                             bool watchdog_ok, bool registers_valid,
                             bool locally_blocked) {
  return registers_valid && watchdog_ok && !locally_blocked &&
         (seq_new != seq_last);
}

}  // namespace greenhouse
