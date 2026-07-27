#include "greenhouse_controller.h"
#include "esphome/core/log.h"

namespace esphome {
namespace greenhouse_controller {

static const char *const TAG = "greenhouse_controller";

void GreenhouseController::dump_config() {
  ESP_LOGCONFIG(TAG, "Greenhouse Controller:");
  ESP_LOGCONFIG(TAG, "  target_temp=%.1f max_temp=%.1f emergency_temp=%.1f",
                sp_.target_temp, sp_.max_temp, sp_.emergency_temp);
  ESP_LOGCONFIG(TAG, "  target_vpd=%.2f deadband=%.2f leaf_offset=%.1f",
                sp_.target_vpd, sp_.vpd_deadband, sp_.leaf_offset);
}

Actions GreenhouseController::supervise(Mode requested, float t_air, float rh,
                                        float age_s, float timeout_s,
                                        bool comm_ok) {
  using namespace greenhouse;
  Actions a;
  a.mode = requested;

  // Prio 1: Kommunikations-/Sicherheitsausfall
  if (!comm_ok) {
    a.mode = MODE_EMERGENCY;
    a.exhaust = true;
    a.recirc_fan_pct = sp_.fan_min;
    a.alarm = true;
    return a;
  }

  if (requested == MODE_OFF || requested == MODE_MAINTENANCE) {
    a.exhaust = (requested == MODE_OFF);
    a.recirc_fan_pct = 0.0f;
    return a;
  }

  // Prio 2: Sensorfehler des Gewächshaussensors
  const bool sensor_ok =
      temp_valid(t_air) && rh_valid(rh) && sensor_fresh(age_s, timeout_s);
  if (!sensor_ok) {
    a.mode = MODE_EMERGENCY;
    a.exhaust = true;
    a.recirc_fan_pct = sp_.fan_min;
    a.alarm = true;
    return a;
  }

  a.led_allowed = true;
  a.recirc_fan_pct = sp_.fan_min;
  a.irrigation_allowed =
      (requested == MODE_AUTO_TEMPERATURE || requested == MODE_AUTO_VPD ||
       requested == MODE_IRRIGATION || requested == MODE_MANUAL);

  // Prio 3: Übertemperatur
  if (t_air >= sp_.emergency_temp) {
    a.mode = MODE_EMERGENCY;
    a.exhaust = true;
    a.recirc_fan_pct = sp_.fan_emergency;
    a.led_allowed = false;
    a.irrigation_allowed = false;
    a.alarm = true;
    return a;
  }
  if (t_air >= sp_.max_temp) {
    a.exhaust = true;
    a.recirc_fan_pct = sp_.fan_max;
    a.humidifier = false;
    return a;
  }

  // Prio 4: Untertemperatur
  if (t_air <= sp_.min_temp) {
    a.exhaust = false;
    a.recirc_fan_pct = sp_.fan_min;
    return a;
  }

  // Prio 5: Kondensationsschutz
  if ((t_air - dew_point_c(t_air, rh)) < 1.5f) {
    a.exhaust = true;
    a.dehumidifier = true;
    a.recirc_fan_pct = sp_.fan_min > 50.0f ? sp_.fan_min : 50.0f;
    return a;
  }

  // Prio 6: Maximale Luftfeuchte
  if (rh >= sp_.max_humidity) {
    a.exhaust = true;
    a.dehumidifier = true;
    a.recirc_fan_pct = sp_.fan_min > 50.0f ? sp_.fan_min : 50.0f;
    return a;
  }

  // Prio 7: VPD
  if (requested == MODE_AUTO_VPD) {
    const float vpd = vpd_leaf_kpa(t_air, rh, sp_.leaf_offset);
    const float low = sp_.target_vpd - sp_.vpd_deadband;
    const float high = sp_.target_vpd + sp_.vpd_deadband;
    if (vpd < low) {
      a.dehumidifier = true;
      a.recirc_fan_pct = sp_.fan_min > 50.0f ? sp_.fan_min : 50.0f;
    } else if (vpd > high) {
      a.humidifier = true;
      a.recirc_fan_pct = sp_.fan_min;
    }
    return a;
  }

  // Prio 7b: reine Temperaturregelung
  if (requested == MODE_AUTO_TEMPERATURE) {
    const float span =
        (sp_.max_temp - sp_.target_temp) > 0.1f ? (sp_.max_temp - sp_.target_temp) : 0.1f;
    const float over = (t_air - sp_.target_temp) > 0.0f ? (t_air - sp_.target_temp) : 0.0f;
    float frac = over / span;
    if (frac > 1.0f) frac = 1.0f;
    a.recirc_fan_pct = sp_.fan_min + frac * (sp_.fan_max - sp_.fan_min);
    a.exhaust = t_air >= (sp_.target_temp + span * 0.5f);
    return a;
  }

  return a;
}

}  // namespace greenhouse_controller
}  // namespace esphome
