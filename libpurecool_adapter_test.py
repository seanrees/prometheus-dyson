"""Unit test for the libpurecool_adapter module."""

import configparser
import unittest

import libpurecool_adapter

from libpurecool import dyson, const


class TestLibpurecoolAdapter(unittest.TestCase):
    def testIdentify(self):
        def makeStub(p): return {'ProductType': p, 'Serial': 'serial'}

        c = configparser.ConfigParser()
        c['360Eye'] = makeStub(const.DYSON_360_EYE)
        c['CoolLinkV1'] = makeStub(const.DYSON_PURE_COOL_LINK_DESK)
        c['CoolV2'] = makeStub(const.DYSON_PURE_COOL)
        c['HotCoolLinkV1'] = makeStub(const.DYSON_PURE_HOT_COOL_LINK_TOUR)
        c['HotCoolV2'] = makeStub(const.DYSON_PURE_HOT_COOL)

        ac = libpurecool_adapter.DysonAccountCache([])
        self.assertIsNone(ac._identify(c['360Eye']))
        self.assertEqual(ac._identify(
            c['CoolLinkV1']), dyson.DysonPureCoolLink)
        self.assertEqual(ac._identify(c['CoolV2']), dyson.DysonPureCool)
        self.assertEqual(ac._identify(
            c['HotCoolLinkV1']), dyson.DysonPureHotCoolLink)
        self.assertEqual(ac._identify(c['HotCoolV2']), dyson.DysonPureHotCool)

    def testLoad(self):
        devices = [
            {'Active': 'true', 'Name': 'first', 'Serial': 'AB1-US-12345678', 'Version': '1.0',
             'LocalCredentials': 'ABCD', 'AutoUpdate': 'true', 'NewVersionAvailable': 'true',
             'ProductType': '455'},        # 455 = Pure Hot+Cool Link (V1)
            {'Active': 'true', 'Name': 'ignore', 'Serial': 'AB2-US-12345678', 'Version': '1.0',
             'LocalCredentials': 'ABCD', 'AutoUpdate': 'true', 'NewVersionAvailable': 'true',
             'ProductType': 'N223'},       # N223 = 360 Eye (we should skip this)
            {'Active': 'true', 'Name': 'third', 'Serial': 'AB3-US-12345678', 'Version': '1.0',
             'LocalCredentials': 'ABCD', 'AutoUpdate': 'true', 'NewVersionAvailable': 'true',
             'ProductType': '438'}         # 438 = Pure Cool (V2)
        ]

        ac = libpurecool_adapter.DysonAccountCache(devices)
        devices = ac.devices()
        self.assertEqual(len(devices), 2)
        self.assertEqual(devices[0].name, 'first')
        self.assertEqual(devices[1].name, 'third')

        ac = libpurecool_adapter.DysonAccountCache([])
        self.assertEqual(len(ac.devices()), 0)


if __name__ == '__main__':
    unittest.main()
