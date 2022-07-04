#!/usr/bin/python3
"""Toggles the heat mode for a Dyson heating fan on or off."""

import argparse
import functools
import logging
import sys
import threading

import config
import connect

import libdyson.dyson_device

logger = logging.getLogger(__name__)

_one_more_event = threading.Event()
_ok_to_shutdown = threading.Event()


def device_callback(
    want_heat_mode: str,
    name: str,
    device: libdyson.dyson_device.DysonFanDevice,
    is_state=False,
    unused_is_environ=False,
) -> None:
    """Callback for libdyson.

    Args:
        want_heat_mode: string, "on" if you want heat turned on, "off" if you want heat turned off.
    """
    # If we sent a command to the device (e.g; enable or disable heat), we need to wait
    # for one more update to confirm the device mode change. Once we have it, we can
    # shutdown.
    if _one_more_event.is_set():
        _ok_to_shutdown.set()
        return

    if is_state:
        current_heat_mode_is_on = device.heat_mode_is_on
        want_heat_on = want_heat_mode == 'on'

        if current_heat_mode_is_on == want_heat_on:
            logger.info(
                'Fan heat for %s (%s) already in desired state of %s',
                name,
                device.serial,
                want_heat_mode.upper(),
            )
            _ok_to_shutdown.set()
            return

        if want_heat_mode == 'off':
            device.disable_heat_mode()
        else:
            device.enable_heat_mode()

        logger.info(
            'Turning %s heat on %s (%s)', want_heat_mode.upper(
            ), name, device.serial
        )
        _one_more_event.set()


turn_on_heat = functools.partial(device_callback, 'on')
turn_off_heat = functools.partial(device_callback, 'off')


def main(argv):
    """Main body of the program."""
    parser = argparse.ArgumentParser(prog=argv[0])
    parser.add_argument(
        '--config', help='Configuration file (INI file)', default='config.ini')
    parser.add_argument(
        '--device', help='Device name (from config) to operate on')
    parser.add_argument(
        '--heat_mode', help='Desired mode, on or off', default='off')
    parser.add_argument(
        '--log_level',
        help='Logging level (DEBUG, INFO, WARNING, ERROR)',
        type=str,
        default='INFO',
    )
    args = parser.parse_args()

    try:
        level = getattr(logging, args.log_level)
    except AttributeError:
        print(f'Invalid --log_level: {args.log_level}')
        sys.exit(-1)
    args = parser.parse_args()

    logging.basicConfig(
        format='%(asctime)s [%(name)24s %(thread)d] %(levelname)10s %(message)s',
        datefmt='%Y/%m/%d %H:%M:%S',
        level=level,
    )

    try:
        cfg = config.Config(args.config)
    except:
        logger.exception('Could not load configuration: %s', args.config)
        sys.exit(-1)

    devices = cfg.devices
    if len(devices) == 0:
        logger.fatal(
            'No devices configured; please re-run this program with --create_device_cache.'
        )
        sys.exit(-2)

    dev = [d for d in devices if d.name == args.device]
    if not dev:
        logger.fatal(
            'Could not find device "%s" in configuration', args.device)
        sys.exit(-3)

    if args.heat_mode == 'on':
        callback_fn = turn_on_heat
    elif args.heat_mode == 'off':
        callback_fn = turn_off_heat
    else:
        logger.fatal('Invalid --heat_mode, must be one of "on" or "off"')
        sys.exit(-3)

    conn_mgr = connect.ConnectionManager(
        callback_fn, dev, cfg.hosts, reconnect=False)

    _ok_to_shutdown.wait()
    conn_mgr.shutdown()


if __name__ == '__main__':
    main(sys.argv)
