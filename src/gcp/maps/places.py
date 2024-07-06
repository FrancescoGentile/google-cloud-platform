# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: Apache-2.0
# ruff: noqa: RUF009

"""Defines classes and functions to work with the Google Maps Places API."""

import dataclasses
import datetime
import enum
from collections.abc import Iterable
from typing import Any, TypeAlias

import dateutil.parser
import serde
from casefy import casefy
from typing_extensions import Self

# --------------------------------------------------------------------------- #
# Components
# --------------------------------------------------------------------------- #

LatLng: TypeAlias = tuple[float, float]
"""A tuple representing a latitude and a longitude."""


class PriceLevel(enum.Enum):
    """Price levels for places."""

    UNSPECIFIED = "unspecified"
    FREE = "free"
    INEXPENSIVE = "inexpensive"
    MODERATE = "moderate"
    EXPENSIVE = "expensive"
    VERY_EXPENSIVE = "very_expensive"

    @classmethod
    def from_api_format(cls, value: str) -> Self:
        """Converts the price level from the format returned by the API."""
        value = value.removeprefix("PRICE_LEVEL_")
        return cls(value.lower())

    def to_api_format(self) -> str:
        """Returns the price level in the format required by the API."""
        return f"PRICE_LEVEL_{self.name}"


class BusinessStatus(enum.Enum):
    """The status of a business."""

    OPERATIONAL = "operational"
    CLOSED_TEMPORARILY = "closed_temporarily"
    CLOSED_PERMANENTLY = "closed_permanently"

    @classmethod
    def from_api_format(cls, value: str) -> Self:
        """Converts the business status from the format returned by the API."""
        return cls(value.lower())

    def to_api_format(self) -> str:
        """Returns the business status in the format required by the API."""
        return self.name


@serde.serde
@dataclasses.dataclass(frozen=True)
class CircularArea:
    """A circular area to search for places.

    Attributes:
        center: The center of the circle as a tuple of latitude and longitude.
        radius: The radius of the circle in meters.
    """

    center: LatLng
    radius: int

    def __post_init__(self) -> None:
        """Validates the properties of the area.

        Raises:
            ValueError: If the radius is not between 1 and 50,000 meters.
        """
        if not 0 < self.radius <= 50_000:
            msg = "Radius must be between 1 and 50,000 meters."
            raise ValueError(msg)

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> Self:
        """Creates a CircularArea instance from the data returned by the API."""
        center = (data["center"]["latitude"], data["center"]["longitude"])
        radius = data["radius"]
        return cls(center, radius)

    def to_api_format(self) -> dict[str, Any]:
        """Returns the area in the format required by the API."""
        return {
            "center": {
                "latitude": self.center[0],
                "longitude": self.center[1],
            },
            "radius": self.radius,
        }


@serde.serde
@dataclasses.dataclass(frozen=True)
class RectangularArea:
    """A rectangular area to search for places.

    Attributes:
        south_west: The south-west corner of the rectangle as a tuple of latitude and
            longitude.
        north_east: The north-east corner of the rectangle as a tuple of latitude and
            longitude.
    """

    south_west: LatLng
    north_east: LatLng

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> Self:
        """Creates a RectangularArea instance from the data returned by the API."""
        south_west = (data["low"]["latitude"], data["low"]["longitude"])
        north_east = (data["high"]["latitude"], data["high"]["longitude"])
        return cls(south_west, north_east)

    def to_api_format(self) -> dict[str, Any]:
        """Returns the area in the format required by the API."""
        return {
            "low": {
                "latitude": self.south_west[0],
                "longitude": self.south_west[1],
            },
            "high": {
                "latitude": self.north_east[0],
                "longitude": self.north_east[1],
            },
        }


Area: TypeAlias = CircularArea | RectangularArea


@serde.serde
@dataclasses.dataclass(frozen=True)
class LocalizedString:
    """A string associated with a language code."""

    text: str
    language_code: str

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> Self:
        """Creates a DisplayName instance from the data returned by the API."""
        data = {casefy.snakecase(key): value for key, value in data.items()}
        return cls(**data)

    def to_api_format(self) -> dict[str, Any]:
        """Returns the display name in the format required by the API."""
        data = dataclasses.asdict(self)
        return {casefy.camelcase(key): value for key, value in data.items()}


@serde.serde
@dataclasses.dataclass(frozen=True)
class AddressComponent:
    """The parts of an address."""

    long_text: str
    short_text: str
    types: list[str]
    language_code: str

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> Self:
        """Creates an AddressComponent instance from the data returned by the API."""
        data = {casefy.snakecase(key): value for key, value in data.items()}
        return cls(**data)

    def to_api_format(self) -> dict[str, Any]:
        """Returns the address component in the format required by the API."""
        data = dataclasses.asdict(self)
        return {casefy.camelcase(key): value for key, value in data.items()}


@serde.serde
class PlusCode:
    """A plus code for a place."""

    global_code: str
    compound_code: str

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> Self:
        """Creates a PlusCode instance from the data returned by the API."""
        global_code = data["globalCode"]
        compound_code = data["compoundCode"]
        return cls(global_code, compound_code)

    def to_api_format(self) -> dict[str, Any]:
        """Returns the plus code in the format required by the API."""
        return {
            "globalCode": self.global_code,
            "compoundCode": self.compound_code,
        }


@serde.serde
@dataclasses.dataclass(frozen=True)
class OpeningHours:
    """The opening hours of a place.

    Attributes:
        periods: A list of lists of tuples representing the opening and closing times
            for each day of the week (starting from Monday).
            The outer list has 7 elements, one for each day of the week, and the inner
            lists contain tuples with the opening and closing times for that day of the
            week. If an opening (resp. closing) time is `None`, it means that the
            opening (resp. closing) time falls in the previous (resp. next) days.
            For example, if the opening interval spans from 23:00 of Monday to 01:00 of
            Tuesday, the closing time will be `None` for Monday and the opening time
            will be `None` for Tuesday. In the extreme case where the place is open
            24/7, all lists will contain a single tuple with `None` for both the opening
            and closing times.
        weekday_descriptions: A list of seven strings representing the formatted
            opening hours for each day of the week. The Places Service will format and
            localize the opening hours appropriately for the current language.
            The ordering of the elements in this array depends on the language.
            Some languages start the week on Monday, while others start on Sunday.
    """

    periods: list[list[tuple[datetime.time | None, datetime.time | None]]]
    weekday_descriptions: list[str]

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> Self:
        """Creates an OpeningHours instance from the data returned by the API."""
        weekday_descriptions = data["weekdayDescriptions"]
        periods = [[] for _ in range(7)]
        for period in data["periods"]:
            start = period["open"]
            end = period.get("close")
            if end is None:
                if len(data["periods"]) > 1:
                    msg = "If you see this message, please report it as a bug."
                    raise RuntimeError(msg)

                # the place is open 24/7
                for i in range(7):
                    periods[i].append((None, None))
                break

            start_day = start["day"]
            end_day = end["day"]
            if start_day == end_day:
                s = datetime.time(start["hour"], start["minute"])
                e = datetime.time(end["hour"], end["minute"])
                periods[start_day].append((s, e))
            else:
                for i in range(start_day, end_day + 1):
                    if i == start_day:
                        s, e = datetime.time(start["hour"], start["minute"]), None
                    elif i == end_day:
                        s, e = None, datetime.time(end["hour"], end["minute"])
                    else:
                        s, e = None, None
                    periods[i].append((s, e))

        # move from Sunday-based to Monday-based
        periods = periods[1:] + [periods[0]]

        return cls(periods, weekday_descriptions)


@serde.serde
@dataclasses.dataclass(frozen=True)
class AuthorAttribution:
    """The author attribution for a given resource."""

    display_name: str
    uri: str | None = None
    photo_uri: str | None = None

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> Self:
        """Creates an AuthorAttributions instance from the data returned by the API."""
        data = {casefy.snakecase(key): value for key, value in data.items()}
        return cls(**data)

    def to_api_format(self) -> dict[str, Any]:
        """Returns the author attributions in the format required by the API."""
        data = dataclasses.asdict(self)
        return {casefy.camelcase(key): value for key, value in data.items()}


@serde.serde
class Photo:
    """A photo of a place."""

    name: str
    height: int
    width: int
    authot_attributions: list[AuthorAttribution]

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> Self:
        """Creates a Photo instance from the data returned by the API."""
        name = data["name"]
        width = data["widthPx"]
        height = data["heightPx"]
        authors = [
            AuthorAttribution.from_api_format(author)
            for author in data["authorAttributions"]
        ]

        return cls(name, height, width, authors)

    def to_api_format(self) -> dict[str, Any]:
        """Returns the photo in the format required by the API."""
        return {
            "name": self.name,
            "widthPx": self.width,
            "heightPx": self.height,
            "authorAttributions": [
                author.to_api_format() for author in self.authot_attributions
            ],
        }


@serde.serde
@dataclasses.dataclass(frozen=True)
class Review:
    """A review of a place."""

    name: str
    relative_publish_time_description: str
    rating: int
    text: LocalizedString
    original_text: LocalizedString
    author_attribution: AuthorAttribution
    publish_time: datetime.datetime

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> Self:
        """Creates a Review instance from the data returned by the API."""
        data = {casefy.snakecase(key): value for key, value in data.items()}
        data["text"] = LocalizedString.from_api_format(data["text"])
        data["original_text"] = LocalizedString.from_api_format(data["original_text"])
        data["author_attribution"] = AuthorAttribution.from_api_format(
            data["author_attribution"]
        )
        data["publish_time"] = dateutil.parser.parse(data["publish_time"])

        return cls(**data)

    def to_api_format(self) -> dict[str, Any]:
        """Returns the review in the format required by the API."""
        data = dataclasses.asdict(self)
        data["text"] = data["text"].to_api_format()
        data["original_text"] = data["original_text"].to_api_format()
        data["author_attribution"] = data["author_attribution"].to_api_format()
        data["publish_time"] = data["publish_time"].isoformat()

        return {casefy.camelcase(key): value for key, value in data.items()}


@serde.serde
@dataclasses.dataclass(frozen=True)
class ParkingOptions:
    """The parking options for a place."""

    free_garage_parking: bool | None = None
    free_parking_lot: bool | None = None
    free_street_parking: bool | None = None
    paid_garage_parking: bool | None = None
    paid_parking_lot: bool | None = None
    paid_street_parking: bool | None = None
    valet_parking: bool | None = None

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> Self:
        """Creates a ParkingOptions instance from the data returned by the API."""
        data = {casefy.snakecase(key): value for key, value in data.items()}
        return cls(**data)

    def to_api_format(self) -> dict[str, Any]:
        """Returns the parking options in the format required by the API."""
        data = dataclasses.asdict(self)
        return {casefy.camelcase(key): value for key, value in data.items()}


@serde.serde
@dataclasses.dataclass(frozen=True)
class PaymentOptions:
    """The payment options for a place."""

    accepts_cash_only: bool | None = None
    accepts_credit_cards: bool | None = None
    accepts_debit_cards: bool | None = None
    accepts_nfc: bool | None = None

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> Self:
        """Creates a PaymentOptions instance from the data returned by the API."""
        data = {casefy.snakecase(key): value for key, value in data.items()}
        return cls(**data)

    def to_api_format(self) -> dict[str, Any]:
        """Returns the payment options in the format required by the API."""
        data = dataclasses.asdict(self)
        return {casefy.camelcase(key): value for key, value in data.items()}


# --------------------------------------------------------------------------- #
# Place Class
# --------------------------------------------------------------------------- #


@serde.serde
@dataclasses.dataclass(frozen=True, repr=False)
class Place:
    """Describes a place returned by the Google Maps API.

    !!! warning

        At the moment, only a subset of the fields returned by the API is supported.
    """

    id: str | None = None
    name: str | None = None
    # basic fields
    accessibility_options: dict[str, bool] | None = None
    address_components: list[AddressComponent] | None = None
    adr_format_address: str | None = None
    business_status: BusinessStatus | None = None
    display_name: LocalizedString | None = None
    formatted_address: str | None = None
    google_maps_uri: str | None = None
    icon_background_color: str | None = None
    icon_mask_base_uri: str | None = None
    location: LatLng | None = None
    photos: list[Photo] | None = None
    plus_code: PlusCode | None = None
    primary_type: str | None = None
    primary_type_display_name: LocalizedString | None = None
    short_formatted_address: str | None = None
    types: list[str] | None = None
    utc_offset_minutes: int | None = None
    viewport: RectangularArea | None = None
    # advanced fields
    current_opening_hours: OpeningHours | None = None
    current_secondary_opening_hours: OpeningHours | None = None
    international_phone_number: str | None = None
    national_phone_number: str | None = None
    price_level: PriceLevel | None = None
    rating: float | None = None
    regular_opening_hours: OpeningHours | None = None
    regular_secondary_opening_hours: OpeningHours | None = None
    user_rating_count: int | None = None
    website_uri: str | None = None
    # preferred fields
    allows_dogs: bool | None = None
    curbside_pickup: bool | None = None
    delivery: bool | None = None
    dine_in: bool | None = None
    good_for_children: bool | None = None
    good_for_groups: bool | None = None
    good_for_watching_sports: bool | None = None
    live_music: bool | None = None
    menu_for_children: bool | None = None
    parking_options: ParkingOptions | None = None
    payment_options: PaymentOptions | None = None
    outdoor_seating: bool | None = None
    reservable: bool | None = None
    restroom: bool | None = None
    reviews: list[Review] | None = None
    serves_beer: bool | None = None
    serves_breakfast: bool | None = None
    serves_brunch: bool | None = None
    serves_cocktails: bool | None = None
    serves_coffee: bool | None = None
    serves_desserts: bool | None = None
    serves_dinner: bool | None = None
    serves_lunch: bool | None = None
    serves_vegetarian_food: bool | None = None
    serves_wine: bool | None = None
    takeout: bool | None = None

    @classmethod
    def from_api_format(cls, data: dict[str, Any]) -> Self:
        """Creates a Place instance from the data returned by the API.

        Args:
            data: The data returned by the API.

        Returns:
            The Place instance.
        """
        values = {}
        valid_fields = {f.name for f in dataclasses.fields(Place)}
        for key, value in data.items():
            key, value = _from_api_format(key, value)  # noqa: PLW2901
            if key in valid_fields:
                values[key] = value

        return cls(**values)

    def __repr__(self) -> str:
        """Returns a string representation of the place."""
        fields = []
        for field in dataclasses.fields(self):
            value = getattr(self, field.name)
            if value is not None:
                fields.append(f"{field.name}={value!r}")

        return f"{self.__class__.__name__}({', '.join(fields)})"


# --------------------------------------------------------------------------- #
# Helper Functions
# --------------------------------------------------------------------------- #


def create_field_mask(fields: Iterable[str], *, add_prefix: bool) -> str:
    """Creates a field mask from a list of field names.

    Args:
        fields: The field names to include in the mask. Use "*" to include all fields.
        add_prefix: Whether to add the `places.` prefix to the field names.

    Returns:
        The field mask as a comma-separated string.

    Raises:
        ValueError: If no fields are provided.
        ValueError: If an invalid field name is provided. A field name is invalid if
            it is not a field of the class.
    """
    fields = set(fields)
    if len(fields) == 0:
        msg = "At least one field must be provided."
        raise ValueError(msg)

    valid_fields = {f.name for f in dataclasses.fields(Place)}

    if "*" in fields:
        return "*"

    invalid_fields = fields - valid_fields
    if len(invalid_fields) > 0:
        msg = f"Invalid field(s): {', '.join(invalid_fields)}"
        raise ValueError(msg)

    return ",".join(_to_api_name(field, add_prefix=add_prefix) for field in fields)


def _to_api_name(field: str, *, add_prefix: bool) -> str:
    """Converts a field name to the corresponding API field name.

    Args:
        field: The field name to convert.
        add_prefix: Whether to add the `places.` prefix to the field name.

    Returns:
        The corresponding API field name.
    """
    # transform from snake_case to camelCase
    field = casefy.camelcase(field)
    if add_prefix:
        field = f"places.{field}"

    return field


def _from_api_format(key: str, value: Any) -> tuple[str, Any]:  # noqa: C901, PLR0912
    """Converts a field from the API format to the class format.

    Args:
        key: The field name in the API format.
        value: The field value in the API format.

    Returns:
        A tuple containing the field name and the field value in the class format.
    """
    key = casefy.snakecase(key)
    match key:
        case "accessibility_options":
            value = {casefy.snakecase(k): v for k, v in value.items()}
        case "address_components":
            value = [AddressComponent.from_api_format(data) for data in value]
        case "business_status":
            value = BusinessStatus.from_api_format(value)
        case "display_name":
            value = LocalizedString.from_api_format(value)
        case "location":
            value = (value["latitude"], value["longitude"])
        case "photos":
            value = [Photo.from_api_format(data) for data in value]
        case "plus_code":
            value = PlusCode.from_api_format(value)
        case "primary_type_display_name":
            value = LocalizedString.from_api_format(value)
        case "viewport":
            value = RectangularArea.from_api_format(value)
        case (
            "current_opening_hours"
            | "current_secondary_opening_hours"
            | "regular_opening_hours"
            | "regular_secondary_opening_hours"
        ):
            value = OpeningHours.from_api_format(value)
        case "price_level":
            value = PriceLevel.from_api_format(value)
        case "parking_options":
            value = ParkingOptions.from_api_format(value)
        case "payment_options":
            value = PaymentOptions.from_api_format(value)
        case "reviews":
            value = [Review.from_api_format(data) for data in value]
        case _:
            pass

    return key, value
