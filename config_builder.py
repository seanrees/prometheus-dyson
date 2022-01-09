"""Implements device-lookup via libdyson to produce a local credential cache.

This is based heavily on shenxn@'s implementation of get_devices.py:
https://github.com/shenxn/libdyson/blob/main/get_devices.py
"""

import argparse
import configparser
import io
import logging
import sys

from typing import Dict, List, Tuple, Optional

from libdyson import DEVICE_TYPE_NAMES, get_mqtt_info_from_wifi_info
from libdyson.cloud import DysonAccount, DysonDeviceInfo
from libdyson.cloud.account import DysonAccountCN
from libdyson.exceptions import DysonOTPTooFrequently, DysonLoginFailure

import config


def _query_credentials() -> config.DysonLinkCredentials:
    """Asks the user for their DysonLink/Cloud credentials.

    Returns:
      DysonLinkCredentials based on what the user supplied
    """
    print('First, we need your app/DysonLink login details.')
    print('This is used to get a list of your devices from Dyson. This')
    print('should be the same username&password you use to login into')
    print('the Dyson app (e.g; on your phone:')
    username = input('Username (or number phone if in China): ')
    password = input('Password: ')
    country = input('Country code (e.g; IE): ')

    return config.DysonLinkCredentials(username, password, country)


def _query_wifi() -> Tuple[str, str, str]:
    """Asks the user for their DysonLink/Cloud credentials.

    Returns:
      DysonLinkCredentials based on what the user supplied
    """
    print('This requires the WiFi credentials from the label on the Dyson')
    print('device. This will be used to calculate the secret required')
    print('to connect to this device locally. This script does NOT need')
    print('to modify WiFi settings in any way.')
    print('')
    print('The product SSID might look like: DYSON-AB0-XX-ABC1234D-123')
    print('')
    ssid = input('Enter product SSID            : ')
    password = input('Enter product WiFi password   : ')
    name = input('Device name (e.g; Living Room): ')
    return (ssid, password, name)


def _query_dyson(creds: config.DysonLinkCredentials) -> List[DysonDeviceInfo]:
    """Queries Dyson's APIs for a device list.

    This function requires user interaction, to check either their mobile or email
    for a one-time password.

    Args:
      username: email address or mobile number (mobile if country is CN)
      password: login password
      country: two-letter country code for account, e.g; IE, CN

    Returns:
      list of DysonDeviceInfo
    """
    username = creds.username
    country = creds.country

    if country == 'CN':
        # Treat username like a phone number and use login_mobile_otp.
        account = DysonAccountCN()
        if not username.startswith('+86'):
            username = '+86' + username

        print(
            f'Please check your mobile device ({username}) for a one-time password.')
        verify_fn = account.login_mobile_otp(username)
    else:
        account = DysonAccount()
        verify_fn = account.login_email_otp(username, country)
        print(f'Please check your email ({username}) for a one-time password.')

    print()
    otp = input('Enter OTP: ')
    try:
        verify_fn(otp, creds.password)
        return account.devices()
    except DysonLoginFailure:
        print('Incorrect OTP.')
        sys.exit(-1)


def write_config(filename: str, creds: Optional[config.DysonLinkCredentials],
                 devices: List[DysonDeviceInfo], hosts: Dict[str, str]) -> None:
    """Writes the config out to filename.

    Args:
        filename: relative or fully-qualified path to the config file (ini format)
        creds: DysonLinkCredentials with Dyson username/password/country.
        devices: a list of Devices
        hosts: a serial->IP address (or host) map for direct (non-zeroconf) connection
    """
    cfg = configparser.ConfigParser()

    if creds:
        cfg['Dyson Link'] = {
            'Username': creds.username,
            'Password': creds.password,
            'Country': creds.country
        }

    cfg['Hosts'] = hosts

    for dev in devices:
        cfg[dev.serial] = {
            'Name': dev.name,
            'Serial': dev.serial,
            'LocalCredentials': dev.credential,
            'ProductType': dev.product_type
        }

    input('Configuration generated; press return to view.')

    buf = io.StringIO()
    cfg.write(buf)

    print(buf.getvalue())
    print('--------------------------------------------------------------------------------')
    print(f'Answering yes to the following question will overwrite {filename}')
    ack = input('Does this look reasonable? [Y/N]: ')
    if len(ack) > 0 and ack.upper()[0] == 'Y':
        with open(filename, 'w') as f:
            cfg.write(f)
        print(f'Config written to {filename}.')
    else:
        print('Received negative answer; nothing written.')


def main(argv):
    """Main body of the program."""
    parser = argparse.ArgumentParser(prog=argv[0])
    parser.add_argument(
        '--log_level',
        help='Logging level (DEBUG, INFO, WARNING, ERROR)',
        type=str,
        default='ERROR')
    parser.add_argument(
        '--config',
        help='Configuration file (INI file)',
        default='/etc/prometheus-dyson/config.ini')
    parser.add_argument(
        '--mode',
        help='Use "wifi" to add devices from WiFi credentials, "cloud" to try via Dyson Link"',
        default='cloud'
    )
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

    print('Welcome to the prometheus-dyson config builder.')

    if args.mode not in ('cloud', 'wifi'):
        print(f'Invalid --mode: {args.mode}, must be one of "cloud" or "wifi"')
        sys.exit(-2)

    cfg = None
    creds = None
    hosts = {}
    try:
        cfg = config.Config(args.config)
        creds = cfg.dyson_credentials
        hosts = cfg.hosts
    except:
        logging.info(
            'Could not load configuration: %s (assuming no configuration)', args.config)

    if args.mode == 'cloud':
        if not creds:
            print('')
            creds = _query_credentials()
        else:
            print(f'Using Dyson credentials from {args.config}')

        try:
            print()
            devices = _query_dyson(creds)
            print(f'Found {len(devices)} devices.')
        except DysonOTPTooFrequently:
            print(
                'DysonOTPTooFrequently: too many OTP attempts, please wait and try again')
            sys.exit(-1)
    else:
        ssid, password, name = _query_wifi()
        serial, credential, product_type = get_mqtt_info_from_wifi_info(
            ssid, password)

        devices = [DysonDeviceInfo(
            name=name,
            active=True,
            version='unknown',
            new_version_available=False,
            auto_update=False,
            serial=serial,
            credential=credential,
            product_type=product_type
        )]

    print()
    write_config(args.config, creds, devices, hosts)


if __name__ == '__main__':
    main(sys.argv)
