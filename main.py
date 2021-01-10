#!/usr/bin/python3
"""Exports Dyson Pure Hot+Cool (DysonLink) statistics as Prometheus metrics.

This module depends on two libraries to function:   pip install
libpurecool   pip install prometheus_client
"""

import argparse
import collections
import configparser
import functools
import logging
import sys
import time

from typing import Callable

from libpurecool import dyson
import prometheus_client                    # type: ignore[import]

from metrics import Metrics

DysonLinkCredentials = collections.namedtuple(
    'DysonLinkCredentials', ['username', 'password', 'country'])


class DysonClient:
    """Connects to and monitors Dyson fans."""

    def __init__(self, username, password, country):
        self.username = username
        self.password = password
        self.country = country

        self._account = None

    def login(self) -> bool:
        """Attempts a login to DysonLink, returns True on success (False
        otherwise)."""
        self._account = dyson.DysonAccount(
            self.username, self.password, self.country)
        if not self._account.login():
            logging.critical(
                'Could not login to Dyson with username %s', self.username)
            return False

        return True

    def monitor(self, update_fn: Callable[[str, str, object], None], only_active=True) -> None:
        """Sets up a background monitoring thread on each device.

        Args:
          update_fn: callback function that will receive the device name, serial number, and
              Dyson*State message for each update event from a device.
          only_active: if True, will only setup monitoring on "active" devices.
        """
        devices = self._account.devices()
        for dev in devices:
            if only_active and not dev.active:
                logging.info('Found device "%s" (serial=%s) but is not active; skipping',
                             dev.name, dev.serial)
                continue

            connected = dev.auto_connect()
            if not connected:
                logging.error('Could not connect to device "%s" (serial=%s); skipping',
                              dev.name, dev.serial)
                continue

            logging.info('Monitoring "%s" (serial=%s)', dev.name, dev.serial)
            wrapped_fn = functools.partial(update_fn, dev.name, dev.serial)

            # Populate initial state values. Without this, we'll run without fan operating
            # state until the next change event (which could be a while).
            wrapped_fn(dev.state)
            dev.add_message_listener(wrapped_fn)


def _sleep_forever() -> None:
    """Sleeps the calling thread until a keyboard interrupt occurs."""
    while True:
        try:
            time.sleep(1)
        except KeyboardInterrupt:
            break


def _read_config(filename):
    """Reads configuration file.

    Returns DysonLinkCredentials or None on error.
    """
    config = configparser.ConfigParser()

    logging.info('Reading "%s"', filename)

    try:
        config.read(filename)
    except configparser.Error as ex:
        logging.critical('Could not read "%s": %s', filename, ex)
        return None

    try:
        username = config['Dyson Link']['username']
        password = config['Dyson Link']['password']
        country = config['Dyson Link']['country']
        return DysonLinkCredentials(username, password, country)
    except KeyError as ex:
        logging.critical('Required key missing in "%s": %s', filename, ex)

    return None


def main(argv):
    """Main body of the program."""
    parser = argparse.ArgumentParser(prog=argv[0])
    parser.add_argument('--port', help='HTTP server port',
                        type=int, default=8091)
    parser.add_argument(
        '--config', help='Configuration file (INI file)', default='config.ini')
    parser.add_argument(
        '--log_level', help='Logging level (DEBUG, INFO, WARNING, ERROR)', type=str, default='INFO')
    parser.add_argument(
        '--include_inactive_devices',
        help='Monitor devices marked as inactive by Dyson (default is only active)',
        action='store_true')
    args = parser.parse_args()

    try:
        level = getattr(logging, args.log_level)
    except AttributeError:
        print(f'Invalid --log_level: {args.log_level}')
        sys.exit(-1)
    args = parser.parse_args()

    logging.basicConfig(
        format='%(asctime)s %(levelname)10s %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S',
        level=level)

    logging.info('Starting up on port=%s', args.port)

    if args.include_inactive_devices:
        logging.info('Including devices marked "inactive" from the Dyson API')

    credentials = _read_config(args.config)
    if not credentials:
        sys.exit(-1)

    metrics = Metrics()
    prometheus_client.start_http_server(args.port)

    client = DysonClient(credentials.username,
                         credentials.password, credentials.country)
    if not client.login():
        sys.exit(-1)

    client.monitor(
        metrics.update, only_active=not args.include_inactive_devices)
    _sleep_forever()


if __name__ == '__main__':
    main(sys.argv)
