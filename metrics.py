"""Creates and maintains Prometheus metric values."""

import logging

from libpurecool import const, dyson_pure_state, dyson_pure_state_v2
from prometheus_client import Gauge, Enum, REGISTRY


# An astute reader may notice this value seems to be slightly wrong.
# The definition is 0 K = -273.15 C, but it appears Dyson use this
# slightly rounded value instead.
KELVIN_TO_CELSIUS = -273


def enum_values(cls):
    return [x.value for x in list(cls)]


def update_gauge(gauge, name: str, serial: str, value):
    gauge.labels(name=name, serial=serial).set(value)


def update_enum(enum, name: str, serial: str, state):
    enum.labels(name=name, serial=serial).state(state)


class Metrics:
    """Registers/exports and updates Prometheus metrics for DysonLink fans."""

    def __init__(self, registry=REGISTRY):
        labels = ['name', 'serial']

        def make_gauge(name, documentation):
            return Gauge(name, documentation, labels, registry=registry)

        def make_enum(name, documentation, state_cls):
            return Enum(name, documentation, labels, states=enum_values(state_cls), registry=registry)

        # Environmental Sensors (v1 & v2 common)
        self.humidity = make_gauge(
            'dyson_humidity_percent', 'Relative humidity (percentage)')
        self.temperature = make_gauge(
            'dyson_temperature_celsius', 'Ambient temperature (celsius)')
        self.voc = make_gauge(
            'dyson_volatile_organic_compounds_units', 'Level of Volatile organic compounds')

        # Environmental Sensors (v1 units only)
        self.dust = make_gauge('dyson_dust_units',
                               'Level of Dust (V1 units only)')

        # Environmental Sensors (v2 units only)
        # Not included: p10r and p25r as they are marked as "unknown" in libpurecool.
        self.pm25 = make_gauge(
            'dyson_pm25_units', 'Level of PM2.5 particulate matter (V2 units only)')
        self.pm10 = make_gauge(
            'dyson_pm10_units', 'Level of PM10 particulate matter (V2 units only)')
        self.nox = make_gauge('dyson_nitrogen_oxide_units',
                              'Level of nitrogen oxides (NOx, V2 units only)')

        # Operational State (v1 & v2 common)
        # Not included: tilt (known values: "OK", others?), standby_monitoring.
        # Synthesised: fan_mode (for V2), fan_power & auto_mode (for V1)
        self.fan_mode = make_enum(
            'dyson_fan_mode', 'Current mode of the fan', const.FanMode)
        self.fan_power = make_enum(
            'dyson_fan_power_mode', 'Current power mode of the fan (like fan_mode but binary)', const.FanPower)
        self.auto_mode = make_enum(
            'dyson_fan_auto_mode', 'Current auto mode of the fan (like fan_mode but binary)', const.AutoMode)
        self.fan_state = make_enum(
            'dyson_fan_state', 'Current running state of the fan', const.FanState)
        self.fan_speed = make_gauge(
            'dyson_fan_speed_units', 'Current speed of fan (-1 = AUTO)')
        self.oscillation = make_enum(
            'dyson_oscillation_mode', 'Current oscillation mode', const.Oscillation)
        self.night_mode = make_enum(
            'dyson_night_mode', 'Night mode', const.NightMode)
        self.heat_mode = make_enum(
            'dyson_heat_mode', 'Current heat mode', const.HeatMode)
        self.heat_state = make_enum(
            'dyson_heat_state', 'Current heat state', const.HeatState)
        self.heat_target = make_gauge(
            'dyson_heat_target_celsius', 'Heat target temperature (celsius)')

        # Operational State (v1 only)
        self.focus_mode = make_enum(
            'dyson_focus_mode', 'Current focus mode (V1 units only)', const.FocusMode)
        self.quality_target = make_gauge(
            'dyson_quality_target_units', 'Quality target for fan (V1 units only)')
        self.filter_life = make_gauge(
            'dyson_filter_life_seconds', 'Remaining HEPA filter life (seconds, V1 units only)')

        # Operational State (v2 only)
        # Not included: oscillation (known values: "ON", "OFF", "OION", "OIOF") using oscillation_state instead
        self.continuous_monitoring = make_enum(
            'dyson_continuous_monitoring_mode', 'Monitor air quality continuously (V2 units only)', const.ContinuousMonitoring)
        self.carbon_filter_life = make_gauge(
            'dyson_carbon_filter_life_percent', 'Percent remaining of carbon filter (V2 units only)')
        self.hepa_filter_life = make_gauge(
            'dyson_hepa_filter_life_percent', 'Percent remaining of HEPA filter (V2 units only)')
        self.night_mode_speed = make_gauge(
            'dyson_night_mode_fan_speed_units', 'Night mode fan speed (V2 units only)')
        self.oscillation_angle_low = make_gauge(
            'dyson_oscillation_angle_low_degrees', 'Low oscillation angle (V2 units only)')
        self.oscillation_angle_high = make_gauge(
            'dyson_oscillation_angle_high_degrees', 'High oscillation angle (V2 units only)')
        self.dyson_front_direction_mode = make_enum(
            'dyson_front_direction_mode', 'Airflow direction from front (V2 units only)', const.FrontalDirection)

    def update(self, name: str, serial: str, message: object) -> None:
        """Receives device/environment state and updates Prometheus metrics.

        Args:
          name: (str) Name of device.
          serial: (str) Serial number of device.
          message: must be one of a DysonEnvironmentalSensor{,V2}State, DysonPureHotCool{,V2}State
          or DysonPureCool{,V2}State.
        """
        if not name or not serial:
            logging.error(
                'Ignoring update with name=%s, serial=%s', name, serial)

        logging.debug('Received update for %s (serial=%s): %s',
                      name, serial, message)

        if isinstance(message, dyson_pure_state.DysonEnvironmentalSensorState):
            self.updateEnvironmentalState(name, serial, message)
        elif isinstance(message, dyson_pure_state_v2.DysonEnvironmentalSensorV2State):
            self.updateEnvironmentalV2State(name, serial, message)
        elif isinstance(message, dyson_pure_state.DysonPureCoolState):
            self.updatePureCoolState(name, serial, message)
        elif isinstance(message, dyson_pure_state_v2.DysonPureCoolV2State):
            self.updatePureCoolV2State(name, serial, message)
        else:
            logging.warning('Received unknown update from "%s" (serial=%s): %s; ignoring',
                            name, serial, type(message))

    def updateEnviromentalStateCommon(self, name: str, serial: str, message):
        temp = round(message.temperature + KELVIN_TO_CELSIUS, 1)

        update_gauge(self.humidity, name, serial, message.humidity)
        update_gauge(self.temperature, name, serial, temp)

    def updateEnvironmentalState(self, name: str, serial: str, message: dyson_pure_state.DysonEnvironmentalSensorState):
        self.updateEnviromentalStateCommon(name, serial, message)

        update_gauge(self.dust, name, serial, message.dust)
        update_gauge(self.voc, name, serial,
                     message.volatil_organic_compounds)

    def updateEnvironmentalV2State(self, name: str, serial: str, message: dyson_pure_state_v2.DysonEnvironmentalSensorV2State):
        self.updateEnviromentalStateCommon(name, serial, message)

        update_gauge(self.pm25, name, serial,
                     message.particulate_matter_25)
        update_gauge(self.pm10, name, serial,
                     message.particulate_matter_10)

        # Previously, Dyson normalised the VOC range from [0,10]. Issue #5
        # discovered on V2 devices, the range is [0, 100]. NOx seems to be
        # similarly ranged. For compatibility and consistency we rerange the values
        # values to the original [0,10].
        voc = message.volatile_organic_compounds/10
        nox = message.nitrogen_dioxide/10
        update_gauge(self.voc, name, serial, voc)
        update_gauge(self.nox, name, serial, nox)

    def updateHeatStateCommon(self, name: str, serial: str, message):
        # Convert from Decikelvin to to Celsius.
        heat_target = round(int(message.heat_target) /
                            10 + KELVIN_TO_CELSIUS, 1)

        update_enum(self.heat_mode, name, serial, message.heat_mode)
        update_enum(self.heat_state, name, serial, message.heat_state)
        update_gauge(self.heat_target, name, serial, heat_target)

    def updatePureCoolStateCommon(self, name: str, serial: str, message):
        update_enum(self.fan_state, name, serial, message.fan_state)
        update_enum(self.night_mode, name, serial, message.night_mode)

        # The API can return 'AUTO' rather than a speed when the device is in
        # automatic mode. Provide -1 to keep it an int.
        speed = message.speed
        if speed == 'AUTO':
            speed = -1
        update_gauge(self.fan_speed, name, serial, speed)

    def updatePureCoolState(self, name: str, serial: str, message: dyson_pure_state.DysonPureCoolState):
        self.updatePureCoolStateCommon(name, serial, message)

        update_enum(self.fan_mode, name, serial, message.fan_mode)
        update_enum(self.oscillation, name, serial, message.oscillation)
        update_gauge(self.quality_target, name,
                     serial, message.quality_target)

        # Synthesize compatible values for V2-originated metrics:
        auto = const.AutoMode.AUTO_OFF.value
        power = const.FanPower.POWER_OFF.value
        if message.fan_mode == const.FanMode.AUTO.value:
            auto = const.AutoMode.AUTO_ON.value
        if message.fan_mode in (const.FanMode.AUTO.value, const.FanMode.FAN.value):
            power = const.FanPower.POWER_ON.value

        update_enum(self.auto_mode, name, serial, auto)
        update_enum(self.fan_power, name, serial, power)

        # Convert filter_life from hours to seconds.
        filter_life = int(message.filter_life) * 60 * 60
        update_gauge(self.filter_life, name, serial, filter_life)

        # Metrics only available with DysonPureHotCoolState
        if isinstance(message, dyson_pure_state.DysonPureHotCoolState):
            self.updateHeatStateCommon(name, serial, message)
            update_enum(self.focus_mode, name, serial, message.focus_mode)

    def updatePureCoolV2State(self, name: str, serial: str, message: dyson_pure_state_v2.DysonPureCoolV2State):
        self.updatePureCoolStateCommon(name, serial, message)

        update_enum(self.fan_power, name, serial, message.fan_power)
        update_enum(self.continuous_monitoring, name,
                    serial, message.continuous_monitoring)
        update_enum(self.dyson_front_direction_mode,
                    name, serial, message.front_direction)

        update_gauge(self.carbon_filter_life, name, serial,
                     int(message.carbon_filter_state))
        update_gauge(self.hepa_filter_life, name, serial,
                     int(message.hepa_filter_state))
        update_gauge(self.night_mode_speed, name, serial,
                     int(message.night_mode_speed))

        # V2 provides oscillation_status and oscillation as fields,
        # oscillation_status provides values compatible with V1, so we use that.
        # oscillation returns as 'OION', 'OIOF.'
        update_enum(self.oscillation, name, serial,
                    message.oscillation_status)
        update_gauge(self.oscillation_angle_low, name,
                     serial, int(message.oscillation_angle_low))
        update_gauge(self.oscillation_angle_high, name,
                     serial, int(message.oscillation_angle_high))

        # Maintain compatibility with the V1 fan metrics.
        fan_mode = const.FanMode.OFF.value
        if message.auto_mode == const.AutoMode.AUTO_ON.value:
            fan_mode = 'AUTO'
        elif message.fan_power == const.FanPower.POWER_ON.value:
            fan_mode = 'FAN'
        else:
            logging.warning('Received unknown fan_power setting from "%s" (serial=%s): %s, defaulting to "%s',
                            name, serial, message.fan_mode, fan_mode)
        update_enum(self.fan_mode, name, serial, fan_mode)

        if isinstance(message, dyson_pure_state_v2.DysonPureHotCoolV2State):
            self.updateHeatStateCommon(name, serial, message)
