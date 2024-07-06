# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: Apache-2.0

"""Module for the Google Maps API."""

from . import places
from ._client import Client
from ._exceptions import APIError

__all__ = [
    # _client
    "Client",
    # _exceptions
    "APIError",
    # places
    "places",
]
