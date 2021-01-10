"""Unit test for the metrics library.

This test is primarily intended to ensure the metrics codepaths for V1
and V2 devices are executed in case folks working on the codebase have one
type of unit and not the other.

The underlying libpurecool Dyson{PureCool,EnvironmentalSensor}{,V2}State
classes take JSON as an input. To make authoring this test a bit more
straightforward, we provide local stubs for each type and a simplified
initialiser to set properties. This comes at the cost of some boilerplate
and possible fragility down the road.
"""


import enum
import unittest

from libpurecool import const, dyson_pure_state, dyson_pure_state_v2
from prometheus_client import registry

import metrics

# pylint: disable=too-few-public-methods


class KeywordInitialiserMixin:
    def __init__(self, *unused_args, **kwargs):
        for k, val in kwargs.items():
            setattr(self, '_' + k, val)


class DysonEnvironmentalSensorState(KeywordInitialiserMixin, dyson_pure_state.DysonEnvironmentalSensorState):
    pass


class DysonPureCoolState(KeywordInitialiserMixin, dyson_pure_state.DysonPureCoolState):
    pass


class DysonPureHotCoolState(KeywordInitialiserMixin, dyson_pure_state.DysonPureHotCoolState):
    pass


class DysonEnvironmentalSensorV2State(KeywordInitialiserMixin, dyson_pure_state_v2.DysonEnvironmentalSensorV2State):
    pass


class DysonPureCoolV2State(KeywordInitialiserMixin, dyson_pure_state_v2.DysonPureCoolV2State):
    pass


class DysonPureHotCoolV2State(KeywordInitialiserMixin, dyson_pure_state_v2.DysonPureHotCoolV2State):
    pass


class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.registry = registry.CollectorRegistry(auto_describe=True)
        self.metrics = metrics.Metrics(registry=self.registry)

    def testEnumValues(self):
        testEnum = enum.Enum('testEnum', 'RED GREEN BLUE')
        self.assertEqual(metrics.enum_values(testEnum), [1, 2, 3])

    def testEnvironmentalSensorState(self):
        args = {
            'humidity': 50,
            'temperature': 21.0 - metrics.KELVIN_TO_CELSIUS,
            'volatil_compounds': 5,
            'dust': 4
        }
        self.assertExpectedValues(DysonEnvironmentalSensorState, args, expected={
            'dyson_humidity_percent': args['humidity'],
            'dyson_temperature_celsius': args['temperature'] + metrics.KELVIN_TO_CELSIUS,
            'dyson_volatile_organic_compounds_units': args['volatil_compounds'],
            'dyson_dust_units': args['dust']
        })

    def testEnvironmentalSensorStateV2(self):
        args = {
            'humidity': 50,
            'temperature': 21.0 - metrics.KELVIN_TO_CELSIUS,
            'volatile_organic_compounds': 50,
            'particulate_matter_25': 2,
            'particulate_matter_10': 10,
            'nitrogen_dioxide': 4,
        }
        self.assertExpectedValues(DysonEnvironmentalSensorV2State, args, expected={
            'dyson_humidity_percent': args['humidity'],
            'dyson_temperature_celsius': args['temperature'] + metrics.KELVIN_TO_CELSIUS,
            'dyson_volatile_organic_compounds_units': args['volatile_organic_compounds']/10,
            'dyson_nitrogen_oxide_units': args['nitrogen_dioxide']/10,
            'dyson_pm25_units': args['particulate_matter_25'],
            'dyson_pm10_units': args['particulate_matter_10'],
        })

    def testPureCoolState(self):
        args = {
            'fan_mode': const.FanMode.FAN.value,
            'fan_state': const.FanState.FAN_ON.value,
            'speed': const.FanSpeed.FAN_SPEED_4.value,
            'night_mode': const.NightMode.NIGHT_MODE_OFF.value,
            'oscilation': const.Oscillation.OSCILLATION_ON.value,
            'filter_life': 1,       # hour.
            'quality_target': const.QualityTarget.QUALITY_NORMAL.value,
        }
        # We can't currently test Enums, so we skip those for now and only evaluate gauges.
        self.assertExpectedValues(DysonPureCoolState, args, expected={
            'dyson_fan_speed_units': int(args['speed']),
            'dyson_filter_life_seconds': 1 * 60 * 60,
            'dyson_quality_target_units': int(args['quality_target'])
        })

        # Test the auto -> -1 conversion.
        args.update({
            'fan_mode': const.FanMode.AUTO.value,
            'speed': 'AUTO',
        })
        self.assertExpectedValues(DysonPureCoolState, args, expected={
            'dyson_fan_speed_units': -1
        })

        # Test the heat type.
        args.update({
            'fan_focus': const.FocusMode.FOCUS_OFF.value,
            # Decikelvin
            'heat_target': (24 - metrics.KELVIN_TO_CELSIUS) * 10,
            'heat_mode': const.HeatMode.HEAT_ON.value,
            'heat_state': const.HeatState.HEAT_STATE_ON.value
        })
        self.assertExpectedValues(DysonPureHotCoolState, args, expected={
            'dyson_heat_target_celsius': 24
        })

    def testPureCoolStateV2(self):
        args = {
            'fan_power': const.FanPower.POWER_ON.value,
            'front_direction': const.FrontalDirection.FRONTAL_ON.value,
            'auto_mode': const.AutoMode.AUTO_ON.value,
            'oscillation_status': const.Oscillation.OSCILLATION_ON.value,
            'oscillation': const.OscillationV2.OSCILLATION_ON.value,
            'night_mode': const.NightMode.NIGHT_MODE_OFF.value,
            'continuous_monitoring': const.ContinuousMonitoring.MONITORING_ON.value,
            'fan_state': const.FanState.FAN_ON.value,
            'night_mode_speed': const.FanSpeed.FAN_SPEED_2.value,
            'speed': const.FanSpeed.FAN_SPEED_10.value,
            'carbon_filter_state': 50.0,
            'hepa_filter_state': 60.0,
            'oscillation_angle_low': 100.0,
            'oscillation_angle_high': 180.0,
        }
        self.assertExpectedValues(DysonPureCoolV2State, args, expected={
            'dyson_fan_speed_units': int(args['speed']),
            'dyson_night_mode_fan_speed_units': int(args['night_mode_speed']),
            'dyson_carbon_filter_life_percent': int(args['carbon_filter_state']),
            'dyson_hepa_filter_life_percent': int(args['hepa_filter_state']),
            'dyson_oscillation_angle_low_degrees': args['oscillation_angle_low'],
            'dyson_oscillation_angle_high_degrees': args['oscillation_angle_high']
        })

        # Test the heat type.
        args.update({
            # Decikelvin
            'heat_target': (24 - metrics.KELVIN_TO_CELSIUS) * 10,
            'heat_mode': const.HeatMode.HEAT_ON.value,
            'heat_state': const.HeatState.HEAT_STATE_ON.value
        })
        self.assertExpectedValues(DysonPureHotCoolV2State, args, expected={
            'dyson_heat_target_celsius': 24
        })

    def assertExpectedValues(self, cls, args, expected):
        labels = {'name': 'n', 'serial': 's'}

        obj = cls(**args)
        self.metrics.update(labels['name'], labels['serial'], obj)
        for k, want in expected.items():
            got = self.registry.get_sample_value(k, labels)
            self.assertEqual(got, want, f'metric {k} (class={cls.__name__})')


if __name__ == '__main__':
    unittest.main()
