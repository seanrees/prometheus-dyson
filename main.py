#!/usr/bin/python3
"""Exports Dyson Pure Hot+Cool (DysonLink) statistics as Prometheus metrics.

This module depends on two libraries to function:   pip install
libpurecool   pip install prometheus_client
"""

import argparse
import functools
import logging
import sys
import time

from typing import Callable, Dict, List, Optional

import prometheus_client                    # type: ignore[import]

import account
import config
import libpurecool_adapter
from metrics import Metrics


class DysonClient:
    """Connects to and monitors Dyson fans."""

    def __init__(self, device_cache: List[Dict[str, str]], hosts: Optional[Dict] = None):
        self._account = libpurecool_adapter.DysonAccountCache(device_cache)
        self.hosts = hosts or {}

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

            manual_ip = self.hosts.get(dev.serial.upper())
            if manual_ip:
                logging.info('Attempting connection to device "%s" (serial=%s) via configured IP %s',
                             dev.name, dev.serial, manual_ip)
                connected = dev.connect(manual_ip)
            else:
                logging.info('Attempting to discover device "%s" (serial=%s) via zeroconf',
                             dev.name, dev.serial)
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


def main(argv):
    """Main body of the program."""
    parser = argparse.ArgumentParser(prog=argv[0])
    parser.add_argument('--port', help='HTTP server port',
                        type=int, default=8091)
    parser.add_argument(
        '--config', help='Configuration file (INI file)', default='config.ini')
    parser.add_argument('--create_device_cache',
                        help='Performs a one-time login to Dyson to locally cache device information. Use this for the first invocation of this binary or when you add/remove devices.', action='store_true')
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

    try:
        cfg = config.Config(args.config)
    except:
        logging.exception('Could not load configuration: %s', args.config)
        sys.exit(-1)

    devices = cfg.devices
    if not len(devices):
        logging.fatal(
            'No devices configured; please re-run this program with --create_device_cache.')
        sys.exit(-2)

    if args.create_device_cache:
        logging.info(
            '--create_device_cache supplied; breaking out to perform this.')
        account.generate_device_cache(cfg.dyson_credentials, args.config)
        sys.exit(0)

    metrics = Metrics()
    prometheus_client.start_http_server(args.port)

    client = DysonClient(devices, cfg.hosts)
    client.monitor(
        metrics.update, only_active=not args.include_inactive_devices)
    _sleep_forever()


if __name__ == '__main__':
    main(sys.argv)
