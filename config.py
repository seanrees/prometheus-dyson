"""Manages configuration file."""

import collections
import configparser
import copy
import logging
from typing import Dict, List, Optional

DysonLinkCredentials = collections.namedtuple(
    'DysonLinkCredentials', ['username', 'password', 'country'])


class Config:
    def __init__(self, filename: str):
        self._filename = filename
        self._config = self.load(filename)

    def load(self, filename: str):
        """Reads configuration file.

        Returns DysonLinkCredentials or None on error, and a dict of
        configured device serial numbers mapping to IP addresses
        """
        config = configparser.ConfigParser()

        logging.info('Reading "%s"', filename)

        try:
            config.read(filename)
        except configparser.Error as ex:
            logging.critical('Could not read "%s": %s', filename, ex)
            raise ex

        return config

    @property
    def dyson_credentials(self) -> Optional[DysonLinkCredentials]:
        try:
            username = self._config['Dyson Link']['username']
            password = self._config['Dyson Link']['password']
            country = self._config['Dyson Link']['country']
            return DysonLinkCredentials(username, password, country)
        except KeyError as ex:
            logging.critical(
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
            logging.debug(
                'No "Hosts" section found in config file, no manual IP overrides are available')

        # Convert the hosts tuple (('serial0', 'ip0'), ('serial1', 'ip1'))
        # into a dict {'SERIAL0': 'ip0', 'SERIAL1': 'ip1'}, making sure that
        # the serial keys are upper case (configparser downcases everything)
        return {h[0].upper(): h[1] for h in hosts}

    @property
    def devices(self) -> List[object]:
        """Consumes all sections looking for device entries.

        A device looks a bit like this:
        [AB1-UK-AAA0111A]
        name = Living room
        active = true
        localcredentials = 12345==
        serial = AB1-UK-AAA0111A
        ... (and a few other fields)

        Returns:
          A list of dict-like objects. This interface is unstable; do not rely on it.
        """
        sections = self._config.sections()

        ret = []
        for s in sections:
            if not self._config.has_option(s, 'LocalCredentials'):
                # This is probably not a device entry, so ignore it.
                continue

            # configparser returns a dict-like type here with case-insensitive keys. This is an effective
            # stand-in for the type that libpurecool expects, and a straightforward to thing to change
            # as we move towards libdyson's API.
            ret.append(copy.deepcopy(self._config[s]))

        return ret
