from __future__ import annotations

from typing import TypeVar

import cqrs

ResultT = TypeVar("ResultT", bound=cqrs.Response | None, default=None)


class Command(cqrs.Request[ResultT]):
    """Base command DTO. The type parameter is the value ``mediator.send`` returns."""


class CommandResult(cqrs.Response):
    """Base command result DTO."""
