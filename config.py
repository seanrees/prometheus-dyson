"""Manages configuration file."""

import collections
import configparser
import logging
from typing import Dict, List, Optional

Device = collections.namedtuple(
    'Device', ['name', 'serial', 'credentials', 'product_type'])

DysonLinkCredentials = collections.namedtuple(
    'DysonLinkCredentials', ['username', 'password', 'country'])

logger = logging.getLogger(__name__)


class Config:
    """Reads the configuration file and provides handy accessors.

    Args:
      filename: path (absolute or relative) to the config file (ini format).
    """

    def __init__(self, filename: str):
        self._filename = filename
        self._config = self.load(filename)

    @classmethod
    def load(cls, filename: str):
        """Reads configuration file.

        Returns DysonLinkCredentials or None on error, and a dict of
        configured device serial numbers mapping to IP addresses
        """
        config = configparser.ConfigParser()

        logger.info('Reading "%s"', filename)

        try:
            config.read(filename)
        except configparser.Error as ex:
            logger.critical('Could not read "%s": %s', filename, ex)
            raise ex

        return config

    @property
    def dyson_credentials(self) -> Optional[DysonLinkCredentials]:
        """Cloud Dyson API credentials.

        In the config, this looks like:
        [Dyson Link]
        username = user
        password = pass
        country = XX

        Returns:
          DysonLinkCredentials.
        """
        try:
            username = self._config['Dyson Link']['username']
            password = self._config['Dyson Link']['password']
            country = self._config['Dyson Link']['country']
            return DysonLinkCredentials(username, password, country)
        except KeyError as ex:
            logger.warning(
                'Required key missing in "%s": %s', self._filename, ex)
            return None

    @property
    def hosts(self) -> Dict[str, str]:
        """Loads the Hosts section, which is a serial -> IP address override.

        This is useful if you don't want to discover devices using zeroconf. The Hosts section
        looks like this:

        [Hosts]
        AB1-UK-AAA0111A = 192.168.1.2
        """
        try:
            hosts = self._config.items('Hosts')
        except configparser.NoSectionError:
            hosts = []
            logger.debug(
                'No "Hosts" section found in config file, no manual IP overrides are available')

        # Convert the hosts tuple (('serial0', 'ip0'), ('serial1', 'ip1'))
        # into a dict {'SERIAL0': 'ip0', 'SERIAL1': 'ip1'}, making sure that
        # the serial keys are upper case (configparser downcases everything)
        return {h[0].upper(): h[1] for h in hosts}

    @property
    def devices(self) -> List[Device]:
        """Consumes all sections looking for device entries.

        A device looks a bit like this:
        [AB1-UK-AAA0111A]
        name = Living room
        active = true
        localcredentials = 12345==
        serial = AB1-UK-AAA0111A
        ... (and a few other fields)

        Returns:
          A list of Device objects.
        """
        sections = self._config.sections()

        ret = []
        for sect in sections:
            if not self._config.has_option(sect, 'LocalCredentials'):
                # This is probably not a device entry, so ignore it.
                continue

            ret.append(Device(
                self._config[sect]['Name'],
                self._config[sect]['Serial'],
                self._config[sect]['LocalCredentials'],
                self._config[sect]['ProductType']))

        return ret
