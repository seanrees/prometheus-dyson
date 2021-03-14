"""Unit test for the libpurecool_adapter module."""

import unittest

from libpurecool import dyson, const

import libpurecool_adapter


class TestLibpurecoolAdapter(unittest.TestCase):
    def testGetDevice(self):
        name = 'name'
        serial = 'serial'
        credentials = 'credentials'

        test_cases = {
            const.DYSON_PURE_COOL_LINK_DESK: dyson.DysonPureCoolLink,
            const.DYSON_PURE_COOL: dyson.DysonPureCool,
            const.DYSON_PURE_HOT_COOL_LINK_TOUR: dyson.DysonPureHotCoolLink,
            const.DYSON_PURE_HOT_COOL: dyson.DysonPureHotCool
        }
        for product_type, want in test_cases.items():
            got = libpurecool_adapter.get_device(name, serial, credentials, product_type)
            self.assertIsInstance(got, want)

        got = libpurecool_adapter.get_device(name, serial, credentials, const.DYSON_360_EYE)
        self.assertIsNone(got)


if __name__ == '__main__':
    unittest.main()
