"""Creates and maintains Prometheus metric values."""

import datetime
import enum
import logging

import libdyson
import libdyson.const
import libdyson.dyson_device

from prometheus_client import Gauge, Enum, REGISTRY


# An astute reader may notice this value seems to be slightly wrong.
# The definition is 0 K = -273.15 C, but it appears Dyson use this
# slightly rounded value instead.
KELVIN_TO_CELSIUS = -273


def enum_values(cls):
    return [x.value for x in list(cls)]


def update_gauge(gauge, name: str, serial: str, value):
    gauge.labels(name=name, serial=serial).set(value)


def update_env_gauge(gauge, name: str, serial, value):
    if value in (libdyson.const.ENVIRONMENTAL_OFF, libdyson.const.ENVIRONMENTAL_FAIL):
        return
    if value == libdyson.const.ENVIRONMENTAL_INIT:
        value = 0
    update_gauge(gauge, name, serial, value)


def update_enum(enum_metric, name: str, serial: str, state):
    enum_metric.labels(name=name, serial=serial).state(state)


def timestamp() -> str:
    return f'{int(datetime.datetime.now().timestamp())}'


class OffOn(enum.Enum):
    OFF = 'OFF'
    ON = 'ON'

    @staticmethod
    def translate_bool(value: bool):
        return OffOn.ON.value if value else OffOn.OFF.value


class OffFan(enum.Enum):
    OFF = 'OFF'
    FAN = 'FAN'

    @staticmethod
    def translate_bool(value: bool):
        return OffFan.FAN.value if value else OffFan.OFF.value


class OffFanAuto(enum.Enum):
    OFF = 'OFF'
    FAN = 'FAN'
    AUTO = 'AUTO'


class OffOnIdle(enum.Enum):
    OFF = 'OFF'
    ON = 'ON'
    IDLE = 'IDLE'


class OffHeat(enum.Enum):
    OFF = 'OFF'
    HEAT = 'HEAT'

    @staticmethod
    def translate_bool(value: bool):
        return OffHeat.HEAT.value if value else OffHeat.OFF.value


class Metrics:
    """Registers/exports and updates Prometheus metrics for DysonLink fans."""

    def __init__(self, registry=REGISTRY):
        labels = ['name', 'serial']

        def make_gauge(name, documentation):
            return Gauge(name, documentation, labels, registry=registry)

        def make_enum(name, documentation, state_cls):
            return Enum(name, documentation, labels, states=enum_values(state_cls),
                        registry=registry)

        # Last update timestamps. Use Gauge here as we can set arbitrary
        # values; Counter requires inc().
        self.last_update_state = make_gauge(
            'dyson_last_state_timestamp_seconds',
            'Last Unix time we received an STATE update')

        self.last_update_environmental = make_gauge(
            'dyson_last_environmental_timestamp_seconds',
            'Last Unix timestamp we received an ENVIRONMENTAL update')

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
            'dyson_fan_mode', 'Current mode of the fan', OffFanAuto)
        self.fan_power = make_enum(
            'dyson_fan_power_mode',
            'Current power mode of the fan (like fan_mode but binary)',
            OffOn)
        self.auto_mode = make_enum(
            'dyson_fan_auto_mode', 'Current auto mode of the fan (like fan_mode but binary)',
            OffOn)
        self.fan_state = make_enum(
            'dyson_fan_state', 'Current running state of the fan', OffFan)
        self.fan_speed = make_gauge(
            'dyson_fan_speed_units', 'Current speed of fan (-1 = AUTO)')
        self.oscillation = make_enum(
            'dyson_oscillation_mode', 'Current oscillation mode (will the fan move?)', OffOn)
        self.oscillation_state = make_enum(
            'dyson_oscillation_state', 'Current oscillation state (is the fan moving?)', OffOnIdle)
        self.night_mode = make_enum(
            'dyson_night_mode', 'Night mode', OffOn)
        self.heat_mode = make_enum(
            'dyson_heat_mode', 'Current heat mode', OffHeat)
        self.heat_state = make_enum(
            'dyson_heat_state', 'Current heat state', OffHeat)
        self.heat_target = make_gauge(
            'dyson_heat_target_celsius', 'Heat target temperature (celsius)')
        self.continuous_monitoring = make_enum(
            'dyson_continuous_monitoring_mode', 'Monitor air quality continuously', OffOn)

        # Operational State (v1 only)
        self.focus_mode = make_enum(
            'dyson_focus_mode', 'Current focus mode (V1 units only)', OffOn)
        self.quality_target = make_gauge(
            'dyson_quality_target_units', 'Quality target for fan (V1 units only)')
        self.filter_life = make_gauge(
            'dyson_filter_life_seconds', 'Remaining HEPA filter life (seconds, V1 units only)')

        # Operational State (v2 only)
        self.carbon_filter_life = make_gauge(
            'dyson_carbon_filter_life_percent',
            'Percent remaining of carbon filter (V2 units only)')
        self.hepa_filter_life = make_gauge(
            'dyson_hepa_filter_life_percent', 'Percent remaining of HEPA filter (V2 units only)')
        self.night_mode_speed = make_gauge(
            'dyson_night_mode_fan_speed_units', 'Night mode fan speed (V2 units only)')
        self.oscillation_angle_low = make_gauge(
            'dyson_oscillation_angle_low_degrees', 'Low oscillation angle (V2 units only)')
        self.oscillation_angle_high = make_gauge(
            'dyson_oscillation_angle_high_degrees', 'High oscillation angle (V2 units only)')
        self.dyson_front_direction_mode = make_enum(
            'dyson_front_direction_mode', 'Airflow direction from front (V2 units only)', OffOn)

    def update(self, name: str, device: libdyson.dyson_device.DysonFanDevice, is_state=False,
               is_environmental=False) -> None:
        """Receives device/environment state and updates Prometheus metrics.

        Args:
          name: device name (e.g; "Living Room")
          device: a libdyson.Device instance.
          is_state: is a device state (power, fan mode, etc) update.
          is_enviromental: is an environmental (temperature, humidity, etc) update.
        """
        if not device:
            logging.error('Ignoring update, device is None')

        serial = device.serial

        heating = isinstance(device, libdyson.dyson_device.DysonHeatingDevice)

        if isinstance(device, libdyson.DysonPureCool):
            if is_environmental:
                self.update_v2_environmental(name, device)
            if is_state:
                self.update_v2_state(name, device, heating)
        elif isinstance(device, libdyson.DysonPureCoolLink):
            if is_environmental:
                self.update_v1_environmental(name, device)
            if is_state:
                self.update_v1_state(name, device, heating)
        else:
            logging.warning('Received unknown update from "%s" (serial=%s): %s; ignoring',
                            name, serial, type(device))

    def update_v1_environmental(self, name: str, device) -> None:
        self.update_common_environmental(name, device)
        update_env_gauge(self.dust, name, device.serial, device.particulates)
        update_env_gauge(self.voc, name, device.serial,
                         device.volatile_organic_compounds)

    def update_v2_environmental(self, name: str, device) -> None:
        self.update_common_environmental(name, device)

        update_env_gauge(self.pm25, name, device.serial,
                         device.particulate_matter_2_5)
        update_env_gauge(self.pm10, name, device.serial,
                         device.particulate_matter_10)

        # Previously, Dyson normalised the VOC range from [0,10]. Issue #5
        # discovered on V2 devices, the range is [0, 100]. NOx seems to be
        # similarly ranged. For compatibility and consistency we rerange the values
        # values to the original [0,10].
        voc = device.volatile_organic_compounds
        nox = device.nitrogen_dioxide
        if voc >= 0:
            voc = voc/10
        if nox >= 0:
            nox = nox/10
        update_env_gauge(self.voc, name, device.serial, voc)
        update_env_gauge(self.nox, name, device.serial, nox)

    def update_common_environmental(self, name: str, device) -> None:
        update_gauge(self.last_update_environmental,
                     name, device.serial, timestamp())

        temp = round(device.temperature + KELVIN_TO_CELSIUS, 1)
        update_env_gauge(self.humidity, name, device.serial, device.humidity)
        update_env_gauge(self.temperature, name, device.serial, temp)

    def update_v1_state(self, name: str, device, is_heating=False) -> None:
        self.update_common_state(name, device)

        update_enum(self.fan_mode, name, device.serial, device.fan_mode)

        update_enum(self.oscillation, name, device.serial,
                    OffOn.translate_bool(device.oscillation))

        quality_target = int(device.air_quality_target.value)
        update_gauge(self.quality_target, name, device.serial, quality_target)

        # Convert filter_life from hours to seconds.
        filter_life = int(device.filter_life) * 60 * 60
        update_gauge(self.filter_life, name, device.serial, filter_life)

        if is_heating:
            self.update_common_heating(name, device)
            update_enum(self.focus_mode, name, device.serial,
                        OffOn.translate_bool(device.focus_mode))

        # Synthesize compatible values for V2-originated metrics:
        update_enum(self.auto_mode, name, device.serial,
                    OffOn.translate_bool(device.auto_mode))

        oscillation_state = OffOnIdle.ON.value if device.oscillation else OffOnIdle.OFF.value
        if device.oscillation and device.auto_mode and not device.fan_state:
            # Compatibility with V2's behaviour for this value.
            oscillation_state = OffOnIdle.IDLE.value

        update_enum(self.oscillation_state, name,
                    device.serial, oscillation_state)

    def update_v2_state(self, name: str, device, is_heating=False) -> None:
        self.update_common_state(name, device)

        update_enum(self.dyson_front_direction_mode,
                    name, device.serial, OffOn.translate_bool(device.front_airflow))
        update_gauge(self.night_mode_speed, name,
                     device.serial, device.night_mode_speed)
        update_enum(self.oscillation, name, device.serial,
                    OffOn.translate_bool(device.oscillation))

        # TODO: figure out a better way than this. 'oscs' is a tri-state:
        # OFF, ON, IDLE. However, libdyson exposes as a bool only (true if ON).
        oscs = device._get_field_value(device._status, 'oscs')
        update_enum(self.oscillation_state, name, device.serial, oscs)

        update_gauge(self.oscillation_angle_low, name,
                     device.serial, device.oscillation_angle_low)
        update_gauge(self.oscillation_angle_high, name,
                     device.serial, device.oscillation_angle_high)

        if device.carbon_filter_life:
            update_gauge(self.carbon_filter_life, name,
                         device.serial, device.carbon_filter_life)

        if device.hepa_filter_life:
            update_gauge(self.hepa_filter_life, name,
                         device.serial, device.hepa_filter_life)

        # Maintain compatibility with the V1 fan metrics.
        fan_mode = OffFanAuto.FAN.value if device.is_on else OffFanAuto.OFF.value
        if device.auto_mode:
            fan_mode = OffFanAuto.AUTO.value
        update_enum(self.fan_mode, name, device.serial, fan_mode)

        if is_heating:
            self.update_common_heating(name, device)

    def update_common_state(self, name: str, device) -> None:
        update_gauge(self.last_update_state, name, device.serial, timestamp())

        update_enum(self.fan_state, name, device.serial,
                    OffFan.translate_bool(device.fan_state))
        update_enum(self.night_mode, name, device.serial,
                    OffOn.translate_bool(device.night_mode))
        update_enum(self.fan_power, name, device.serial,
                    OffOn.translate_bool(device.is_on))
        update_enum(self.continuous_monitoring, name, device.serial,
                    OffOn.translate_bool(device.continuous_monitoring))

        # libdyson will return None if the fan is on automatic.
        speed = device.speed
        if not speed:
            speed = -1
        update_gauge(self.fan_speed, name, device.serial, speed)

    def update_common_heating(self, name: str, device) -> None:
        heat_target = round(device.heat_target + KELVIN_TO_CELSIUS, 1)
        update_gauge(self.heat_target, name, device.serial, heat_target)

        update_enum(self.heat_mode, name, device.serial,
                    OffHeat.translate_bool(device.heat_mode_is_on))
        update_enum(self.heat_state, name, device.serial,
                    OffHeat.translate_bool(device.heat_status_is_on))
