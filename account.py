"""Implements device-lookup via libdyson to produce a local credential cache.

This is based heavily on shenxn@'s implementation of get_devices.py:
https://github.com/shenxn/libdyson/blob/main/get_devices.py
"""

import io
import configparser
import sys

from typing import List

from config import DysonLinkCredentials

from libdyson.cloud import DysonAccount, DysonDeviceInfo
from libdyson.cloud.account import DysonAccountCN
from libdyson.exceptions import DysonOTPTooFrequently


def _query_dyson(username: str, password: str, country: str) -> List[DysonDeviceInfo]:
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
    if country == 'CN':
        # Treat username like a phone number and use login_mobile_otp.
        account = DysonAccountCN()
        if not username.startswith('+86'):
            username = '+86' + username

        print(f'Using Mobile OTP with {username}')
        print(f'Please check your mobile device for a one-time password.')
        verify = account.login_mobile_otp(username)
    else:
        account = DysonAccount()
        verify = account.login_email_otp(username, country)
        print(f'Using Email OTP with {username}')
        print(f'Please check your email for a one-time password.')

    print()
    otp = input('Enter OTP: ')
    verify(otp, password)

    return account.devices()


def generate_device_cache(creds: DysonLinkCredentials, config: str) -> None:
    try:
        devices = _query_dyson(creds.username, creds.password, creds.country)
    except DysonOTPTooFrequently:
        print('DysonOTPTooFrequently: too many OTP attempts, please wait and try again')
        return

    cfg = configparser.ConfigParser()

    print(f'Found {len(devices)} devices.')

    for d in devices:
        cfg[d.serial] = {
            'Active': 'true' if d.active else 'false',
            'Name': d.name,
            'Version': d.version,
            'LocalCredentials': d.credential,
            'AutoUpdate': 'true' if d.auto_update else 'false',
            'NewVersionAvailable': 'true' if d.new_version_available else 'false',
            'ProductType': d.product_type
        }

    buf = io.StringIO()
    cfg.write(buf)

    print('')
    print(f'Add the following to your configuration ({config}):')
    print(buf.getvalue())
