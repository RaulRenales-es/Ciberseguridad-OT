"""Utility and validation helpers."""

from __future__ import annotations

import ipaddress
from typing import Iterable

from config import MAX_COIL_COUNT, MAX_MODBUS_ADDRESS, MAX_MODBUS_COUNT


class ValidationError(ValueError):
    """Raised when CLI inputs or ranges are invalid."""


def validate_ip(ip: str) -> str:
    """Validate IPv4/IPv6 string and return normalized representation."""

    try:
        return str(ipaddress.ip_address(ip))
    except ValueError as exc:
        raise ValidationError(f"Invalid IP address '{ip}'.") from exc


def validate_unit(unit: int) -> int:
    """Validate Modbus unit (slave) ID."""

    if not 0 <= unit <= 247:
        raise ValidationError("Unit ID must be between 0 and 247.")
    return unit


def validate_address(address: int) -> int:
    """Validate a Modbus address."""

    if not 0 <= address <= MAX_MODBUS_ADDRESS:
        raise ValidationError(
            f"Address must be between 0 and {MAX_MODBUS_ADDRESS}."
        )
    return address


def validate_count(count: int, is_coil: bool = False) -> int:
    """Validate item count for read requests."""

    max_count = MAX_COIL_COUNT if is_coil else MAX_MODBUS_COUNT
    if not 1 <= count <= max_count:
        raise ValidationError(f"Count must be between 1 and {max_count}.")
    return count


def validate_range(start: int, count: int, is_coil: bool = False) -> tuple[int, int]:
    """Validate start/count and resulting address range."""

    start = validate_address(start)
    count = validate_count(count, is_coil=is_coil)
    end = start + count - 1
    if end > MAX_MODBUS_ADDRESS:
        raise ValidationError(
            f"Range overflow: start={start}, count={count}, end={end} exceeds {MAX_MODBUS_ADDRESS}."
        )
    return start, count


def parse_int_list(value: str) -> list[int]:
    """Parse comma-separated integer values."""

    try:
        return [int(part.strip()) for part in value.split(",") if part.strip()]
    except ValueError as exc:
        raise ValidationError("Invalid integer list format.") from exc


def parse_bool_list(value: str) -> list[bool]:
    """Parse comma-separated booleans (1/0/true/false)."""

    mapping = {"1": True, "0": False, "true": True, "false": False}
    parsed: list[bool] = []
    for part in value.split(","):
        token = part.strip().lower()
        if token == "":
            continue
        if token not in mapping:
            raise ValidationError(
                "Invalid boolean list. Use comma-separated values from: 1,0,true,false."
            )
        parsed.append(mapping[token])
    return parsed


def ensure_values_fit_range(address: int, values: Iterable[int | bool]) -> None:
    """Ensure a value list can be written from the given address without overflow."""

    values_list = list(values)
    if not values_list:
        raise ValidationError("At least one value must be supplied.")
    end = address + len(values_list) - 1
    if end > MAX_MODBUS_ADDRESS:
        raise ValidationError(
            f"Write range overflow: start={address}, len={len(values_list)}, end={end}."
        )
