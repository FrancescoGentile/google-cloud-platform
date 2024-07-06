# Copyright 2024 Francesco Gentile.
# SPDX-License-Identifier: Apache-2.0

from typing import Any

from typing_extensions import Self


class APIError(Exception):
    """Represents an error returned by the API."""

    def __init__(
        self,
        status_code: int,
        message: str | None = None,
        status: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Initializes the error.

        Args:
            status_code: The status code of the response.
            message: The error message.
            status: The status of the response.
            details: Additional details about the error.
        """
        super().__init__()

        self.status_code = status_code
        """The HTTP status code of the response."""

        self.message = message
        """The error message contained in the response body (if any)."""

        self.status = status
        """The status of the response (if any)."""

        self.details = details
        """Additional details about the error (if any)."""

    @classmethod
    def from_api_response(cls, code: int, response: dict[str, Any]) -> Self:
        """Creates an error from an API response."""
        return cls(
            status_code=code,
            message=response.get("message"),
            status=response.get("status"),
            details=response.get("details"),
        )

    def __str__(self) -> str:
        message = self.message or "Unknown error"
        return f"{self.__class__.__name__}: {message}"
