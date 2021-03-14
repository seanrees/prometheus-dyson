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

from typing import Callable, Dict

import prometheus_client                    # type: ignore[import]
import libdyson                             # type: ignore[import]

import account
import config
import libpurecool_adapter
import metrics


class DeviceWrapper:
    """Wraps a configured device and holds onto the underlying Dyson device
    object."""

    def __init__(self, device: config.Device):
        self._device = device
        self.libdyson = self._create_libdyson_device()
        self.libpurecool = self._create_libpurecool_device()

    @property
    def name(self) -> str:
        """Returns device name, e.g; 'Living Room'"""
        return self._device.name

    @property
    def serial(self) -> str:
        """Returns device serial number, e.g; AB1-XX-1234ABCD"""
        return self._device.serial

    def _create_libdyson_device(self):
        return libdyson.get_device(self.serial, self._device.credentials, self._device.product_type)

    def _create_libpurecool_device(self):
        return libpurecool_adapter.get_device(self.name, self.serial,
                                              self._device.credentials, self._device.product_type)


class ConnectionManager:
    """Manages connections via manual IP or via libdyson Discovery.

    At the moment, callbacks are done via libpurecool.

    Args:
      update_fn: A callable taking a name, serial, and libpurecool update message
      hosts: a dict of serial -> IP address, for direct (non-zeroconf) connections.
    """

    def __init__(self, update_fn: Callable[[str, str, object], None], hosts: Dict[str, str]):
        self._update_fn = update_fn
        self._hosts = hosts

        logging.info('Starting discovery...')
        self._discovery = libdyson.discovery.DysonDiscovery()
        self._discovery.start_discovery()

    def add_device(self, device: config.Device, add_listener=True):
        """Adds and connects to a device.

        This will connect directly if the host is specified in hosts at
        initialisation, otherwise we will attempt discovery via zeroconf.

        Args:
          device: a config.Device to add
          add_listener: if True, will add callback listeners. Set to False if
                        add_device() has been called on this device already.
        """
        wrap = DeviceWrapper(device)

        if add_listener:
            wrap.libpurecool.add_message_listener(
                functools.partial(self._lpc_callback, wrap))

        manual_ip = self._hosts.get(wrap.serial.upper())
        if manual_ip:
            logging.info('Attempting connection to device "%s" (serial=%s) via configured IP %s',
                         device.name, device.serial, manual_ip)
            wrap.libpurecool.connect(manual_ip)
        else:
            logging.info('Attempting to discover device "%s" (serial=%s) via zeroconf',
                         device.name, device.serial)
            callback_fn = functools.partial(self._discovery_callback, wrap)
            self._discovery.register_device(wrap.libdyson, callback_fn)

    @classmethod
    def _discovery_callback(cls, device: DeviceWrapper, address: str):
        # A note on concurrency: used with DysonDiscovery, this will be called
        # back in a separate thread created by the underlying zeroconf library.
        # When we call connect() on libpurecool or libdyson, that code spawns
        # a new thread for MQTT and returns. In other words: we don't need to
        # worry about connect() blocking zeroconf here.
        logging.info('Discovered %s on %s', device.serial, address)
        device.libpurecool.connect(address)

    def _lpc_callback(self, device: DeviceWrapper, message):
        logging.debug('Received update from %s: %s', device.serial, message)
        self._update_fn(device.name, device.serial, message)


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
                        help=('Performs a one-time login to Dyson\'s cloud service '
                              'to identify your devices. This produces a config snippet '
                              'to add to your config, which will be used to connect to '
                              'your device. Use this when you first use this program and '
                              'when you add or remove devices.'),
                        action='store_true')
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
        format='%(asctime)s [%(thread)d] %(levelname)10s %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S',
        level=level)

    logging.info('Starting up on port=%s', args.port)

    if args.include_inactive_devices:
        logging.warning(
            '--include_inactive_devices is now inoperative and will be removed in a future release')

    try:
        cfg = config.Config(args.config)
    except:
        logging.exception('Could not load configuration: %s', args.config)
        sys.exit(-1)

    devices = cfg.devices
    if len(devices) == 0:
        logging.fatal(
            'No devices configured; please re-run this program with --create_device_cache.')
        sys.exit(-2)

    if args.create_device_cache:
        logging.info(
            '--create_device_cache supplied; breaking out to perform this.')
        account.generate_device_cache(cfg.dyson_credentials, args.config)
        sys.exit(0)

    prometheus_client.start_http_server(args.port)

    connect_mgr = ConnectionManager(metrics.Metrics().update, cfg.hosts)
    for dev in devices:
        connect_mgr.add_device(dev)

    _sleep_forever()


if __name__ == '__main__':
    main(sys.argv)
