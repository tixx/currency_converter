# -*- coding: utf-8 -*-

import json
from typing import List
from urllib import request
from urllib.parse import urlencode, quote_plus

from logger import get_logger

LOGGER = get_logger('oxr_client')


class OXRClient(object):
    API_URL = 'https://openexchangerates.org/api/latest.json'

    def __init__(self, app_id: str) -> None:
        self.app_id = app_id

    def __request(self, payload: dict = None) -> dict:
        req = request.Request(self.API_URL + '?' + urlencode(payload, quote_via=quote_plus))
        res = request.urlopen(req)

        if res.getcode() != 200:
            LOGGER.error(res)
            raise OXRStatusError(request, res)
        j = json.loads(res.read().decode("utf-8"))
        if j is None:
            LOGGER.error(res)
            raise OXRDecodeError(request, res)
        return j

    def get_latest(self, base: str = None, symbols: List[str] = None) -> dict:
        payload = dict()
        payload["app_id"] = self.app_id
        if base is not None:
            payload["base"] = base
        if isinstance(symbols, list) or isinstance(symbols, tuple):
            symbols = ",".join(symbols)
        if symbols is not None:
            payload["symbols"] = symbols
        return self.__request(payload)


class OXRError(Exception):
    def __init__(self, req, resp):
        super(OXRError, self).__init__()
        self.request = req
        self.response = resp


class OXRStatusError(OXRError):
    pass


class OXRDecodeError(OXRError):
    pass
