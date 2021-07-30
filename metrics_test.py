"""Unit test for the metrics library.

This test is primarily intended to ensure the metrics codepaths for V1
and V2 devices are executed in case folks working on the codebase have one
type of unit and not the other.

This test is a little gross; it forcibly injects a dict that looks a lot
like unmarshalled JSON from the device into libdyson's handlers. We then
check for the values on the far-side of the Prometheus metrics, which
ensures things are hooked up right, but limits our ability to test. For
example, we cannot currently test enum values with this test.
"""


import enum
import unittest

from prometheus_client import registry
import libdyson

import metrics


NAME = 'test device'
SERIAL = 'XX1-ZZ-1234ABCD'
CREDENTIALS = 'credz'


class TestMetrics(unittest.TestCase):
    def setUp(self):
        self.registry = registry.CollectorRegistry(auto_describe=True)
        self.metrics = metrics.Metrics(registry=self.registry)

    def test_enum_values(self):
        test = enum.Enum('testEnum', 'RED GREEN BLUE')
        self.assertEqual(metrics.enum_values(test), [1, 2, 3])

    def test_update_v1_environmental(self):
        device = libdyson.DysonPureCoolLink(
            SERIAL, CREDENTIALS, libdyson.DEVICE_TYPE_PURE_COOL_LINK)
        payload = {
            'msg': 'ENVIRONMENTAL-CURRENT-SENSOR-DATA',
            'time': '2021-03-17T15:09:23.000Z',
            'data': {'tact': '2956', 'hact': '0047', 'pact': '0005', 'vact': 'INIT', 'sltm': 'OFF'}
        }
        device._handle_message(payload)

        labels = {'name': NAME, 'serial': SERIAL}
        self.metrics.update(NAME, device, is_state=False,
                            is_environmental=True)

        cases = {
            'dyson_temperature_celsius': 22.6,
            'dyson_volatile_organic_compounds_units': 0,
            'dyson_dust_units': 5
        }
        for metric, want in cases.items():
            got = self.registry.get_sample_value(metric, labels)
            self.assertEqual(got, want, f'metric {metric}')

    def test_update_v2_environmental(self):
        device = libdyson.DysonPureCool(
            SERIAL, CREDENTIALS, libdyson.DEVICE_TYPE_PURE_COOL)
        payload = {
            'msg': 'ENVIRONMENTAL-CURRENT-SENSOR-DATA',
            'time': '2021-03-17T15:09:23.000Z',
            'data': {'tact': '2956', 'hact': '0047', 'pm10': '3', 'pm25': 'INIT',
                     'noxl': 30, 'va10': 'INIT', 'sltm': 'OFF'}
        }
        device._handle_message(payload)

        labels = {'name': NAME, 'serial': SERIAL}
        self.metrics.update(NAME, device, is_state=False,
                            is_environmental=True)

        cases = {
            'dyson_temperature_celsius': 22.6,
            'dyson_pm25_units': 0,
            'dyson_pm10_units': 3,
            'dyson_volatile_organic_compounds_units': 0,
            'dyson_nitrogen_oxide_units': 3
        }
        for metric, want in cases.items():
            got = self.registry.get_sample_value(metric, labels)
            self.assertEqual(got, want, f'metric {metric}')

    def test_update_formaldehyde_environmental(self):
        device = libdyson.DysonPureCoolFormaldehyde(
            SERIAL, CREDENTIALS, libdyson.DEVICE_TYPE_PURE_COOL_FORMALDEHYDE)
        payload = {
            'msg': 'ENVIRONMENTAL-CURRENT-SENSOR-DATA',
            'time': '2021-03-17T15:09:23.000Z',
            'data': {'tact': '2956', 'hact': '0047', 'pm10': '3', 'pm25': 'INIT',
                     'noxl': 30, 'va10': 'INIT', 'hcho': '0002', 'hchr': '0003',
                     'sltm': 'OFF'}
        }
        device._handle_message(payload)

        labels = {'name': NAME, 'serial': SERIAL}
        self.metrics.update(NAME, device, is_state=False,
                            is_environmental=True)

        cases = {
            'dyson_formaldehyde_units': 2,
        }
        for metric, want in cases.items():
            got = self.registry.get_sample_value(metric, labels)
            self.assertEqual(got, want, f'metric {metric}')

    def test_update_v1_state(self):
        device = libdyson.DysonPureHotCoolLink(
            SERIAL, CREDENTIALS, libdyson.DEVICE_TYPE_PURE_HOT_COOL_LINK)
        payload = {
            'msg': 'STATE-CHANGE',
            'time': '2021-03-17T15:27:30.000Z',
            'mode-reason': 'PRC',
            'state-reason': 'MODE',
            'product-state': {
                'fmod': ['AUTO', 'FAN'],
                'fnst': ['FAN', 'FAN'],
                'fnsp': ['AUTO', 'AUTO'],
                'qtar': ['0003', '0003'],
                'oson': ['ON', 'ON'],
                'rhtm': ['ON', 'ON'],
                'filf': ['2209', '2209'],
                'ercd': ['NONE', 'NONE'],
                'nmod': ['OFF', 'OFF'],
                'wacd': ['NONE', 'NONE'],
                'hmod': ['OFF', 'OFF'],
                'hmax': ['2960', '2960'],
                'hsta': ['OFF', 'OFF'],
                'ffoc': ['ON', 'ON'],
                'tilt': ['OK', 'OK']},
            'scheduler': {'srsc': 'a58d', 'dstv': '0001', 'tzid': '0001'}}
        device._handle_message(payload)

        labels = {'name': NAME, 'serial': SERIAL}
        self.metrics.update(NAME, device, is_state=True,
                            is_environmental=False)

        cases = {
            'dyson_fan_speed_units': -1,
            'dyson_filter_life_seconds': 2209 * 60 * 60,
            'dyson_quality_target_units': 3,
            'dyson_heat_target_celsius': 23,
        }
        # We can't currently test Enums, so we skip those for now and only evaluate gauges.
        for metric, want in cases.items():
            got = self.registry.get_sample_value(metric, labels)
            self.assertEqual(got, want, f'metric {metric}')

    def test_update_v2_state(self):
        device = libdyson.DysonPureHotCool(
            SERIAL, CREDENTIALS, libdyson.DEVICE_TYPE_PURE_HOT_COOL)
        payload = {
            'msg': 'STATE-CHANGE',
            'time': '2021-03-17T15:27:30.000Z',
            'mode-reason': 'PRC',
            'state-reason': 'MODE',
            'product-state': {
                'auto': ['ON', 'ON'],
                'fpwr': ['ON', 'ON'],
                'fmod': ['AUTO', 'FAN'],
                'fnst': ['FAN', 'FAN'],
                'fnsp': ['AUTO', 'AUTO'],
                'nmdv': ['0002', '0002'],
                'oson': ['ON', 'ON'],
                'oscs': ['ON', 'ON'],
                'osal': ['0136', '0136'],
                'osau': ['0226', '0226'],
                'rhtm': ['ON', 'ON'],
                'cflr': ['0055', '0055'],
                'hflr': ['0097', '0097'],
                'cflt': ['SCOF', 'SCOF'],
                'hflt': ['GCOM', 'GCOM'],
                'ercd': ['NONE', 'NONE'],
                'nmod': ['OFF', 'OFF'],
                'wacd': ['NONE', 'NONE'],
                'hmod': ['OFF', 'OFF'],
                'hmax': ['2960', '2960'],
                'hsta': ['OFF', 'OFF'],
                'fdir': ['ON', 'ON']}}
        device._handle_message(payload)

        labels = {'name': NAME, 'serial': SERIAL}
        self.metrics.update(NAME, device, is_state=True,
                            is_environmental=False)

        # We can't currently test Enums, so we skip those for now and only evaluate gauges.
        cases = {
            'dyson_fan_speed_units': -1,
            'dyson_carbon_filter_life_percent': 55,
            'dyson_hepa_filter_life_percent': 97,
            'dyson_heat_target_celsius': 23,
        }
        for metric, want in cases.items():
            got = self.registry.get_sample_value(metric, labels)
            self.assertEqual(got, want, f'metric {metric}')


if __name__ == '__main__':
    unittest.main()
