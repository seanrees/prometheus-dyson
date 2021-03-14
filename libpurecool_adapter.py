"""An adapter to use libpurecool's Dyson support without the Cloud API."""

import logging
from typing import Optional

from libpurecool import dyson, dyson_device


# We expect unencrypted credentials only, so monkey-patch this.
dyson_device.decrypt_password = lambda s: s


def get_device(name: str, serial: str, credentials: str, product_type: str) -> Optional[object]:
    """Creates a libpurecool DysonDevice based on the input parameters.

    Args:
      name: name of device (e.g; "Living room")
      serial: serial number, e.g; AB1-XX-1234ABCD
      credentials: unencrypted credentials for accessing the device locally
      product_type: stringified int for the product type (e.g; "455")
    """
    device = {'Serial': serial, 'Name': name,
            'LocalCredentials': credentials, 'ProductType': product_type,
            'Version': '', 'AutoUpdate': '', 'NewVersionAvailable': ''}

    if dyson.is_360_eye_device(device):
        logging.info(
            'Identified %s as a Dyson 360 Eye device which is unsupported (ignoring)')
        return None

    if dyson.is_heating_device(device):
        logging.info(
            'Identified %s as a Dyson Pure Hot+Cool Link (V1) device', serial)
        return dyson.DysonPureHotCoolLink(device)
    if dyson.is_dyson_pure_cool_device(device):
        logging.info(
            'Identified %s as a Dyson Pure Cool (V2) device', serial)
        return dyson.DysonPureCool(device)

    if dyson.is_heating_device_v2(device):
        logging.info(
            'Identified %s as a Dyson Pure Hot+Cool (V2) device',serial)
        return dyson.DysonPureHotCool(device)

    # Last chance.
    logging.info('Identified %s as a Dyson Pure Cool Link (V1) device', serial)
    return dyson.DysonPureCoolLink(device)
