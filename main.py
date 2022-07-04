#!/usr/bin/python3
"""Exports Dyson Pure Hot+Cool (DysonLink) statistics as Prometheus metrics."""

import argparse
import logging
import sys
import time

import prometheus_client

import config
import connect
import metrics


logger = logging.getLogger(__name__)


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
    parser.add_argument(
        '--log_level', help='Logging level (DEBUG, INFO, WARNING, ERROR)', type=str, default='INFO')
    parser.add_argument(
        '--include_inactive_devices',
        help='Do not use; this flag has no effect and remains for compatibility only',
        action='store_true')
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
        level=level)

    logger.info('Starting up on port=%s', args.port)

    if args.include_inactive_devices:
        logger.warning(
            '--include_inactive_devices is now inoperative and will be removed in a future release')

    try:
        cfg = config.Config(args.config)
    except:
        logger.exception('Could not load configuration: %s', args.config)
        sys.exit(-1)

    devices = cfg.devices
    if len(devices) == 0:
        logger.fatal(
            'No devices configured; please re-run this program with --create_device_cache.')
        sys.exit(-2)

    prometheus_client.start_http_server(args.port)

    connect.ConnectionManager(metrics.Metrics().update, devices, cfg.hosts)

    _sleep_forever()


if __name__ == '__main__':
    main(sys.argv)
