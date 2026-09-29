from __future__ import annotations

import cqrs


class Command(cqrs.Request):
    """Base command DTO."""


class CommandResult(cqrs.Response):
    """Base command result DTO."""
