# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: Apache-2.0

import asyncio
import os
from collections.abc import Sequence
from typing import Any, Literal

import aiohttp

from . import places
from ._exceptions import APIError


class Client:
    """Client for Google Maps API.

    !!! note

        This client uses the new version of the Maps Places API. If you need to use the
        old version, you can use the `googlemaps` package.
    """

    # ----------------------------------------------------------------------- #
    # Constructor
    # ----------------------------------------------------------------------- #

    def __init__(self, api_key: str | None = None) -> None:
        """Initializes the client.

        Args:
            api_key: The API key to use for requests. If `None`, the client will try to
                read it from the environment variable `GOOGLE_MAPS_API_KEY`.

        Raises:
            ValueError: If the API key is not provided and the environment variable is
                not set.
            ValueError: If the provided API key is invalid.
        """
        self._api_key = api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        if self._api_key is None:
            msg = (
                "An API key must be provided either as an argument or through the "
                "GOOGLE_MAPS_API_KEY environment variable."
            )
            raise ValueError(msg)

        if not self._api_key.startswith("AIza"):
            msg = "The provided API key is invalid."
            raise ValueError(msg)

        self._session = aiohttp.ClientSession()

    # ----------------------------------------------------------------------- #
    # Places API
    # ----------------------------------------------------------------------- #

    async def search_nearby_places(
        self,
        area: places.CircularArea,
        fields: Sequence[str],
        *,
        included_types: Sequence[str] | None = None,
        excluded_types: Sequence[str] | None = None,
        included_primary_types: Sequence[str] | None = None,
        excluded_primary_types: Sequence[str] | None = None,
        language_code: str = "en",
        max_num_results: int = 20,
        rank_by: Literal["popularity", "distance"] = "popularity",
    ) -> list[places.Place]:
        """Performs a nearby search for places.

        !!! note

            This method uses the new version of the Nearby Search API. If you need to
            use the old version, you can use the `googlemaps` package.

        Args:
            area: The area to search in.
            fields: The fields to return for each place. Note that you don't need to
                add the `places.` prefix to the field names.
            included_types: If provided, only places that match at least one of these
                types will be returned.
            excluded_types: If provided, places that match any of these types will be
                excluded from the results.
            included_primary_types: If provided, only places whose primary type matches
                one of these types will be returned.
            excluded_primary_types: If provided, places whose primary type matches any
                of these types will be excluded from the results.
            language_code: The language code to use for results.
            max_num_results: The maximum number of results to return. Must be between 1
                and 20.
            rank_by: The criterion to use for ranking results.

        Returns:
            A list of places that match the search criteria. Only the fields specified
            in the `fields` argument are returned for each place.

        Raises:
            ValueError: If no fields are specified.
            ValueError: If an invalid field name is provided. Invalid field names are
                those that are not part of the `Place` class.
            ValueError: If `max_num_results` is not in the range [1, 20].
            APIError: If the API returns an error.
        """
        if not 0 < max_num_results <= 20:
            msg = "The maximum number of results must be between in the range [1, 20]."
            raise ValueError(msg)

        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": places.create_field_mask(fields, add_prefix=True),
        }

        body = {
            "locationRestriction": {"circle": area.to_api_format()},
            "languageCode": language_code,
            "maxResultCount": max_num_results,
            "rankPreference": rank_by.upper(),
            "includedTypes": included_types or [],
            "excludedTypes": excluded_types or [],
            "includedPrimaryTypes": included_primary_types or [],
            "excludedPrimaryTypes": excluded_primary_types or [],
        }

        async with self._session.post(url, headers=headers, json=body) as response:
            if response.status != 200:
                data = await response.json()
                raise APIError.from_api_response(response.status, data)

            data = await response.json()
            return [places.Place.from_api_format(item) for item in data["places"]]

    async def search_places_by_text(  # noqa: C901, PLR0912
        self,
        query: str,
        fields: Sequence[str],
        *,
        included_type: str | None = None,
        language_code: str = "en",
        bias_area: places.Area | None = None,
        restrict_area: places.Area | None = None,
        page_size: int = 20,
        next_page_token: str | None = None,
        min_rating: float | None = None,
        open_now: bool = False,
        price_levels: Sequence[places.PriceLevel] | None = None,
        rank_by: Literal["relevance", "distance"] = "relevance",
    ) -> tuple[list[places.Place], str | None]:
        """Performs a text search for places.

        !!! note

            This method uses the new version of the Nearby Search API. If you need to
            use the old version, you can use the `googlemaps` package.

        Args:
            query: The text query to search for.
            fields: The fields to return for each place. Note that you don't need to
                add the `places.` prefix to the field names.
            included_type: If provided, only places that match this type will be
                returned.
            language_code: The language code to use for results.
            bias_area: Bias the results towards a specific region, but without excluding
                places outside of it. If provided, this can be either a rectangular or
                a circular area.
            restrict_area: Only places that are inside this area will be returned. If
                provided, this can only be a rectangular area.
            page_size: The number of results to return in each page. Must be between 1
                and 20.
            next_page_token: The token to use to retrieve the next page of results.
            min_rating: If provided, only places with a rating greater than or equal to
                this value will be returned. Must be between 0 and 5 and can increment
                by 0.5 (e.g., 0, 0.5, 1, 1.5, ..., 5). Values are rounded up to the next
                valid rating.
            open_now: Whether to only return places that are open now. Places that do
                not specify their opening hours are returned only if this flag is set to
                `False`.
            price_levels: If provided, only places with one of these price levels will
                be returned. Note that the `FREE` price level cannot be provided.
            rank_by: The criterion to use for ranking results.

        Returns:
            The first element is a list of places that match the search criteria. Only
            the fields specified in the `fields` argument are returned for each place.
            The second element is a token that can be used to retrieve the next page of
            results. If there are no more results, this will be `None`.

        Raises:
            ValueError: If the query is empty.
            ValueError: If no fields are specified.
            ValueError: If an invalid field name is provided. Invalid field names are
                those that are not part of the `Place` class.
            ValueError: If both a bias area and a restrict area are provided.
            ValueError: If a circular area is provided as a restrict area.
            ValueError: If the page size is not in the range [1, 20].
            ValueError: If the minimum rating is not in the range [0, 5].
            ValueError: If the FREE price level is provided.
            APIError: If the API returns an error.
        """
        if len(query) == 0:
            msg = "The query must not be empty."
            raise ValueError(msg)

        if bias_area is not None and restrict_area is not None:
            msg = "You can't specify both a bias area and a restrict area."
            raise ValueError(msg)

        if not 0 < page_size <= 20:
            msg = "The maximum number of results must be between in the range [1, 20]."
            raise ValueError(msg)

        if min_rating is not None and not 0 <= min_rating <= 5:
            msg = "The minimum rating must be between 0 and 5."
            raise ValueError(msg)

        if places.PriceLevel.FREE in (price_levels or []):
            msg = "The FREE price level cannot be used in the price_levels argument."
            raise ValueError(msg)

        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": places.create_field_mask(fields, add_prefix=True),
        }
        body: dict[str, Any] = {
            "textQuery": query,
            "languageCode": language_code,
            "pageSize": page_size,
            "rankPreference": rank_by.upper(),
            "openNow": open_now,
        }
        if included_type is not None:
            # here we assume that if the user provides an include_type, they want to
            # filter by that type strictly
            body["includedType"] = included_type
            body["strictTypeFiltering"] = True
        if next_page_token is not None:
            body["pageToken"] = next_page_token

        if bias_area is not None:
            match bias_area:
                case places.CircularArea():
                    body["locationBias"] = {"circle": bias_area.to_api_format()}
                case places.RectangularArea():
                    body["locationBias"] = {"rectangle": bias_area.to_api_format()}
        if restrict_area is not None:
            if not isinstance(restrict_area, places.RectangularArea):
                msg = "The restrict area must be a rectangular area."
                raise ValueError(msg)

            body["locationRestriction"] = {"rectangle": restrict_area.to_api_format()}
        if min_rating is not None:
            body["minRating"] = min_rating
        if price_levels:
            body["priceLevels"] = [level.to_api_format() for level in price_levels]

        async with self._session.post(url, headers=headers, json=body) as response:
            if response.status != 200:
                data = await response.json()
                raise APIError.from_api_response(response.status, data)

            data = await response.json()
            next_page_token = data.get("nextPageToken")
            results = [places.Place.from_api_format(item) for item in data["places"]]
            return results, next_page_token

    async def get_place_details(
        self,
        place_id: str,
        fields: Sequence[str],
        *,
        language_code: str = "en",
    ) -> places.Place:
        """Retrieves details for a place.

        !!! note

            This method uses the new version of the Nearby Search API. If you need to
            use the old version, you can use the `googlemaps` package.

        Args:
            place_id: The ID of the place to retrieve details for.
            fields: The fields to return for the place.
            language_code: The language code to use for results.

        Returns:
            The details for the place. Only the fields specified in the `fields`
            argument are returned.

        Raises:
            ValueError: If an empty place ID is provided.
            ValueError: If no fields are specified.
            ValueError: If an invalid field name is provided. Invalid field names are
                those that are not part of the `Place` class.
            APIError: If the API returns an error.
        """
        if len(place_id) == 0:
            msg = "The place ID must not be empty."
            raise ValueError(msg)

        url = f"https://places.googleapis.com/v1/places/{place_id}"
        headers = {
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": places.create_field_mask(fields, add_prefix=False),
        }
        params = {"languageCode": language_code}

        async with self._session.get(url, headers=headers, params=params) as response:
            if response.status != 200:
                data = await response.json()
                raise APIError.from_api_response(response.status, data)

            data = await response.json()
            return places.Place.from_api_format(data)

    async def get_photo_uri(
        self,
        photo: places.Photo,
        *,
        max_width: int | None = None,
        max_height: int | None = None,
    ) -> str:
        """Retrieves the uri of a photo of a place.

        Args:
            photo: The photo to retrieve.
            max_width: The maximum desired width of the image. If the image is smaller
                than this, the original image is returned. If the image is larger, it is
                resized to fit the specified width while maintaining the original aspect
                ratio. At least one of `max_width` and `max_height` must be provided, if
                both are provided, the minimum of the two is used.
            max_height: The maximum desired height of the image. If the image is smaller
                than this, the original image is returned. If the image is larger, it is
                resized to fit the specified height while maintaining the original
                aspect ratio. At least one of `max_width` and `max_height` must be
                provided, if both are provided, the minimum of the two is used.

        Returns:
            The URI of the photo.

        Raises:
            ValueError: If both `max_width` and `max_height` are `None`.
            ValueError: If the maximum width is not in the range [1, 4800].
            ValueError: If the maximum height is not in the range [1, 4800].
            APIError: If the API returns an error.
        """
        if max_width is None and max_height is None:
            msg = "At least one of max_width and max_height must be provided."
            raise ValueError(msg)

        if max_width is not None and not 1 <= max_width <= 4800:
            msg = "The maximum width must be between 1 and 4800."
            raise ValueError(msg)

        if max_height is not None and not 1 <= max_height <= 4800:
            msg = "The maximum height must be between 1 and 4800."
            raise ValueError(msg)

        name = photo.name.strip("/")
        url = f"https://places.googleapis.com/v1/{name}/media"
        headers = {"X-Goog-Api-Key": self._api_key}
        parameters: dict[str, int | str] = {"skipHttpRedirect": "true"}
        if max_width is not None:
            parameters["maxWidthPx"] = max_width
        elif max_height is not None:
            parameters["maxHeightPx"] = max_height

        async with self._session.get(url, headers=headers, params=parameters) as resp:
            if resp.status != 200:
                data = await resp.json()
                raise APIError.from_api_response(resp.status, data)

            data = await resp.json()
            return data["photoUri"]

    # ----------------------------------------------------------------------- #
    # Magic Methods
    # ----------------------------------------------------------------------- #

    def __del__(self) -> None:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                task = loop.create_task(self._session.close())
                task.add_done_callback(lambda _: _)
            else:
                loop.run_until_complete(self._session.close())
        except RuntimeError:
            pass
