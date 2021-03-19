"""Unit test for the config module."""

import tempfile
import unittest

import config

EMPTY = ''
GOOD = """
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
        self._empty_file = self.create_temporary_file(EMPTY)
        self.empty = config.Config(self._empty_file.name)

        self._good_file = self.create_temporary_file(GOOD)
        self.good = config.Config(self._good_file.name)

    def tearDown(self):
        self._empty_file.close()
        self._good_file.close()

    @classmethod
    def create_temporary_file(cls, contents: str):
        ret = tempfile.NamedTemporaryFile()
        ret.write(contents.encode('utf-8'))
        ret.flush()
        return ret

    def testDysonCredentials(self):
        self.assertIsNone(self.empty.dyson_credentials)

        creds = self.good.dyson_credentials
        self.assertEqual(creds.username, 'Username')
        self.assertEqual(creds.password, 'Password')
        self.assertEqual(creds.country, 'IE')

    def testHosts(self):
        self.assertTrue(not self.empty.hosts)
        self.assertEqual(self.good.hosts['ABC-UK-12345678'], '1.2.3.4')

    def testDevices(self):
        self.assertEqual(len(self.empty.devices), 0)
        self.assertEqual(len(self.good.devices), 2)

        self.assertEqual(self.good.devices[0].name, 'Living room')
        self.assertEqual(self.good.devices[1].name, 'Bedroom')


if __name__ == '__main__':
    unittest.main()
