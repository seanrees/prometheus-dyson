#!/usr/bin/python3
"""Exports Dyson Pure Hot+Cool (DysonLink) statistics as Prometheus metrics.

This module depends on two libraries to function:
  pip install libpurecoollink
  pip install prometheus_client
"""

import argparse
import collections
import configparser
import functools
import logging
import sys
import time

from typing import Callable

from libpurecoollink import dyson
from libpurecoollink import dyson_pure_state
import prometheus_client

# Rationale:
#    too-many-instance-attributes: refers to Metrics. This is an intentional design choice.
#    too-few-public-methods: refers to Metrics. This is an intentional design choice.
#    no-member: pylint isn't understanding labels() for Gauge and Enum updates.
# pylint: disable=too-many-instance-attributes,too-few-public-methods,no-member

DysonLinkCredentials = collections.namedtuple(
    'DysonLinkCredentials', ['username', 'password', 'country'])

class Metrics():
  """Registers/exports and updates Prometheus metrics for DysonLink fans."""
  def __init__(self):
    labels = ['name', 'serial']

    # Environmental Sensors
    self.humidity = prometheus_client.Gauge('humidity', 'Relative humidity (percentage)', labels)
    self.temperature = prometheus_client.Gauge(
        'temperature', 'Ambient temperature (celsius)', labels)
    self.voc = prometheus_client.Gauge('voc', 'Level of Volatile organic compounds', labels)
    self.dust = prometheus_client.Gauge('dust', 'Level of Dust', labels)

    # Operational State
    # Ignoring: tilt (known values OK), standby_monitoring.
    self.fan_mode = prometheus_client.Enum(
        'fan_mode', 'Current mode of the fan', labels, states=['AUTO', 'FAN'])
    self.fan_state = prometheus_client.Enum(
        'fan_state', 'Current running state of the fan', labels, states=['FAN', 'OFF'])
    self.fan_speed = prometheus_client.Gauge(
        'fan_speed', 'Current speed of fan (-1 = AUTO)', labels)
    self.oscillation = prometheus_client.Enum(
        'oscillation', 'Current oscillation mode', labels, states=['ON', 'OFF'])
    self.focus_mode = prometheus_client.Enum(
        'focus_mode', 'Current focus mode', labels, states=['ON', 'OFF'])
    self.heat_mode = prometheus_client.Enum(
        'heat_mode', 'Current heat mode', labels, states=['HEAT', 'OFF'])
    self.heat_state = prometheus_client.Enum(
        'heat_state', 'Current heat state', labels, states=['HEAT', 'OFF'])
    self.heat_target = prometheus_client.Gauge(
        'heat_target', 'Heat target temperature (celsius)', labels)
    self.quality_target = prometheus_client.Gauge(
        'quality_target', 'Quality target for fan', labels)
    self.filter_life = prometheus_client.Gauge(
        'filter_life', 'Remaining filter life (hours)', labels)

  def update(self, name: str, serial: str, message: object) -> None:
    """Receives a sensor or device state update and updates Prometheus metrics.

    Args:
      name: (str) Name of device.
      serial: (str) Serial number of device.
      message: must be one of a DysonEnvironmentalSensorState or DysonPureHotCoolState.
    """
    if not name or not serial:
      logging.error('Ignoring update with name=%s, serial=%s', name, serial)

    logging.info('Received update for %s (serial=%s): %s', name, serial, message)

    if isinstance(message, dyson_pure_state.DysonEnvironmentalSensorState):
      self.humidity.labels(name=name, serial=serial).set(message.humidity)
      self.temperature.labels(name=name, serial=serial).set(message.temperature - 273)
      self.voc.labels(name=name, serial=serial).set(message.volatil_organic_compounds)
      self.dust.labels(name=name, serial=serial).set(message.dust)
    elif isinstance(message, dyson_pure_state.DysonPureHotCoolState):
      self.fan_mode.labels(name=name, serial=serial).state(message.fan_mode)
      self.fan_state.labels(name=name, serial=serial).state(message.fan_state)

      speed = message.speed
      if speed == 'AUTO':
        speed = -1
      self.fan_speed.labels(name=name, serial=serial).set(speed)

      self.oscillation.labels(name=name, serial=serial).state(message.oscillation)
      self.focus_mode.labels(name=name, serial=serial).state(message.focus_mode)
      self.heat_mode.labels(name=name, serial=serial).state(message.heat_mode)
      self.heat_state.labels(name=name, serial=serial).state(message.heat_state)
      self.heat_target.labels(name=name, serial=serial).set(int(message.heat_target)/10 - 273)
      self.quality_target.labels(name=name, serial=serial).set(message.quality_target)
      self.filter_life.labels(name=name, serial=serial).set(message.filter_life)
    else:
      logging.warning('Received unknown update from "%s" (serial=%s): %s; ignoring',
                      name, serial, type(message))


class DysonClient():
  """Connects to and monitors Dyson fans."""
  def __init__(self, username, password, country):
    self.username = username
    self.password = password
    self.country = country

    self._account = None

  def login(self) -> bool:
    """Attempts a login to DysonLink, returns True on success (False otherwise)."""
    self._account = dyson.DysonAccount(self.username, self.password, self.country)
    if not self._account.login():
      logging.critical('Could not login to Dyson with username %s', self.username)
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

def _read_config(filename) -> DysonLinkCredentials:
  """Reads configuration file. Returns DysonLinkCredentials or None on error."""
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
  parser.add_argument('--port', help='HTTP server port', type=int, default=8091)
  parser.add_argument('--config', help='Configuration file (INI file)', default='config.ini')
  args = parser.parse_args()

  logging.basicConfig(
      format='%(asctime)s %(levelname)10s %(message)s',
      datefmt='%Y/%m/%d %H:%M:%S',
      level=logging.DEBUG)

  logging.info('Starting up on port=%s', args.port)

  credentials = _read_config(args.config)
  if not credentials:
    exit(-1)

  metrics = Metrics()
  prometheus_client.start_http_server(args.port)

  client = DysonClient(credentials.username, credentials.password, credentials.country)
  if not client.login():
    exit(-1)

  client.monitor(metrics.update)
  _sleep_forever()

if __name__ == '__main__':
  main(sys.argv)
