#pragma once
// greenhouse_controller.h — schlanke ESPHome-Komponente, die die reine Logik
// aus vpd_math.h kapselt und für Lambdas/Sensoren nutzbar macht.
// Bewusst ohne eigene Entities: Werte werden per template-sensor/number in
// YAML gelesen. So bleibt die Komponente klein und robust.

#include "esphome/core/component.h"
#include "vpd_math.h"

namespace esphome {
namespace greenhouse_controller {

enum Mode : uint8_t {
  MODE_OFF = 0,
  MODE_MANUAL = 1,
  MODE_AUTO_TEMPERATURE = 2,
  MODE_AUTO_VPD = 3,
  MODE_IRRIGATION = 4,
  MODE_EMERGENCY = 5,
  MODE_MAINTENANCE = 6,
};

struct Setpoints {
  float target_temp = 25.0f;
  float min_temp = 18.0f;
  float max_temp = 30.0f;
  float emergency_temp = 35.0f;
  float target_vpd = 1.0f;
  float vpd_deadband = 0.1f;
  float leaf_offset = -1.0f;
  float fan_min = 25.0f;
  float fan_max = 100.0f;
  float fan_emergency = 100.0f;
  float max_humidity = 80.0f;
};

struct Actions {
  Mode mode = MODE_OFF;
  bool led_allowed = false;
  bool humidifier = false;
  bool dehumidifier = false;
  bool exhaust = false;
  float recirc_fan_pct = 0.0f;
  bool irrigation_allowed = false;
  bool alarm = false;
};

class GreenhouseController : public Component {
 public:
  void setup() override {}
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

  // Reine Rechenfunktionen (Weiterreichung an vpd_math.h)
  float vpd_air(float t, float rh) { return greenhouse::vpd_air_kpa(t, rh); }
  float vpd_leaf(float t, float rh) {
    return greenhouse::vpd_leaf_kpa(t, rh, sp_.leaf_offset);
  }
  float dew_point(float t, float rh) { return greenhouse::dew_point_c(t, rh); }
  float abs_humidity(float t, float rh) {
    return greenhouse::abs_humidity_g_m3(t, rh);
  }

  Setpoints &setpoints() { return sp_; }

  // Prioritätsbasierter Zustandsautomat (Spiegel von ghlib.supervise)
  Actions supervise(Mode requested, float t_air, float rh, float age_s,
                    float timeout_s, bool comm_ok);

 protected:
  Setpoints sp_;
};

}  // namespace greenhouse_controller
}  // namespace esphome
