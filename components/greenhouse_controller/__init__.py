"""ESPHome-Codegen für die External Component `greenhouse_controller`.

Registriert eine schlanke Component mit einstellbaren Sollwerten. Die eigentliche
Regel-/VPD-Logik liegt in vpd_math.h / greenhouse_controller.cpp und wird aus
YAML-Lambdas heraus aufgerufen (z. B. `id(gh).vpd_leaf(t, rh)`).
"""
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID

CODEOWNERS = ["@greenhouse"]
MULTI_CONF = True

greenhouse_ns = cg.esphome_ns.namespace("greenhouse_controller")
GreenhouseController = greenhouse_ns.class_("GreenhouseController", cg.Component)

CONF_TARGET_TEMP = "target_temp"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_EMERGENCY_TEMP = "emergency_temp"
CONF_TARGET_VPD = "target_vpd"
CONF_VPD_DEADBAND = "vpd_deadband"
CONF_LEAF_OFFSET = "leaf_offset"
CONF_FAN_MIN = "fan_min"
CONF_FAN_MAX = "fan_max"
CONF_FAN_EMERGENCY = "fan_emergency"
CONF_MAX_HUMIDITY = "max_humidity"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(GreenhouseController),
        cv.Optional(CONF_TARGET_TEMP, default=25.0): cv.float_,
        cv.Optional(CONF_MIN_TEMP, default=18.0): cv.float_,
        cv.Optional(CONF_MAX_TEMP, default=30.0): cv.float_,
        cv.Optional(CONF_EMERGENCY_TEMP, default=35.0): cv.float_,
        cv.Optional(CONF_TARGET_VPD, default=1.0): cv.float_,
        cv.Optional(CONF_VPD_DEADBAND, default=0.1): cv.float_,
        cv.Optional(CONF_LEAF_OFFSET, default=-1.0): cv.float_,
        cv.Optional(CONF_FAN_MIN, default=25.0): cv.percentage_int,
        cv.Optional(CONF_FAN_MAX, default=100.0): cv.percentage_int,
        cv.Optional(CONF_FAN_EMERGENCY, default=100.0): cv.percentage_int,
        cv.Optional(CONF_MAX_HUMIDITY, default=80.0): cv.percentage_int,
    }
).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    # Setpoints setzen
    sp = cg.RawExpression(f"{var}->setpoints()")
    cg.add(cg.RawStatement(f"{sp}.target_temp = {config[CONF_TARGET_TEMP]};"))
    cg.add(cg.RawStatement(f"{sp}.min_temp = {config[CONF_MIN_TEMP]};"))
    cg.add(cg.RawStatement(f"{sp}.max_temp = {config[CONF_MAX_TEMP]};"))
    cg.add(cg.RawStatement(f"{sp}.emergency_temp = {config[CONF_EMERGENCY_TEMP]};"))
    cg.add(cg.RawStatement(f"{sp}.target_vpd = {config[CONF_TARGET_VPD]};"))
    cg.add(cg.RawStatement(f"{sp}.vpd_deadband = {config[CONF_VPD_DEADBAND]};"))
    cg.add(cg.RawStatement(f"{sp}.leaf_offset = {config[CONF_LEAF_OFFSET]};"))
    cg.add(cg.RawStatement(f"{sp}.fan_min = {float(config[CONF_FAN_MIN])};"))
    cg.add(cg.RawStatement(f"{sp}.fan_max = {float(config[CONF_FAN_MAX])};"))
    cg.add(cg.RawStatement(f"{sp}.fan_emergency = {float(config[CONF_FAN_EMERGENCY])};"))
    cg.add(cg.RawStatement(f"{sp}.max_humidity = {float(config[CONF_MAX_HUMIDITY])};"))
