"""An adapter to use libpurecool's Dyson support without the Cloud API."""

import collections
import logging
from typing import Callable, Dict, List, Optional

from libpurecool import dyson, dyson_device


class DysonAccountCache:
    def __init__(self, device_cache: List[Dict[str, str]]):
        self._devices = self._load(device_cache)

    def _identify(self, device: Dict[str, str]) -> Optional[Callable[[object], object]]:
        if dyson.is_360_eye_device(device):
            logging.info(
                'Identified %s as a Dyson 360 Eye device which is unsupported (ignoring)')
            return None
        elif dyson.is_heating_device(device):
            logging.info(
                'Identified %s as a Dyson Pure Hot+Cool Link (V1) device', device['Serial'])
            return dyson.DysonPureHotCoolLink
        elif dyson.is_dyson_pure_cool_device(device):
            logging.info(
                'Identified %s as a Dyson Pure Cool (V2) device', device['Serial'])
            return dyson.DysonPureCool
        elif dyson.is_heating_device_v2(device):
            logging.info(
                'Identified %s as a Dyson Pure Hot+Cool (V2) device', device['Serial'])
            return dyson.DysonPureHotCool
        else:
            logging.info(
                'Identified %s as a Dyson Pure Cool Link (V1) device', device['Serial'])
            return dyson.DysonPureCoolLink

    def _load(self, device_cache: List[Dict[str, str]]):
        ret = []

        # Monkey-patch this as we store the local credential unencrypted.
        dyson_device.decrypt_password = lambda s: s

        for d in device_cache:
            typ = self._identify(d)
            if typ:
                ret.append(typ(d))

        return ret

    def devices(self):
        return self._devices
