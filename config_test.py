"""Unit test for the config module."""

import tempfile
import unittest

import config

empty = ''
good = """
[Dyson Link]
username = Username
password = Password
country = IE

[Hosts]
ABC-UK-12345678 = 1.2.3.4

[ABC-UK-12345678]
active = true
name = Living room
serial = ABC-UK-12345678
version = 21.04.03
localcredentials = A_Random_String==
autoupdate = True
newversionavailable = True
producttype = 455

[XYZ-UK-12345678]
active = true
name = Bedroom
serial = XYZ-UK-12345678
version = 21.04.03
localcredentials = A_Random_String==
autoupdate = True
newversionavailable = True
producttype = 455
"""


class TestConfig(unittest.TestCase):
    def setUp(self):
        self._empty_file = self.createTemporaryFile(empty)
        self.empty = config.Config(self._empty_file.name)

        self._good_file = self.createTemporaryFile(good)
        self.good = config.Config(self._good_file.name)

    def tearDown(self):
        self._empty_file.close()
        self._good_file.close()

    def createTemporaryFile(self, contents: str):
        ret = tempfile.NamedTemporaryFile()
        ret.write(contents.encode('utf-8'))
        ret.flush()
        return ret

    def testDysonCredentials(self):
        self.assertIsNone(self.empty.dyson_credentials)

        c = self.good.dyson_credentials
        self.assertEqual(c.username, 'Username')
        self.assertEqual(c.password, 'Password')
        self.assertEqual(c.country, 'IE')

    def testHosts(self):
        self.assertTrue(not self.empty.hosts)
        self.assertEqual(self.good.hosts['ABC-UK-12345678'], '1.2.3.4')

    def testDevices(self):
        self.assertEqual(len(self.empty.devices), 0)
        self.assertEqual(len(self.good.devices), 2)

        self.assertEqual(self.good.devices[0]['name'], 'Living room')
        self.assertEqual(self.good.devices[1]['Name'], 'Bedroom')


if __name__ == '__main__':
    unittest.main()
