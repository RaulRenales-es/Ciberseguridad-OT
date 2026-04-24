"""Configuration dataclasses and constants for the Modbus PLC client."""

from dataclasses import dataclass


DEFAULT_PORT: int = 502
DEFAULT_TIMEOUT: float = 3.0
MAX_MODBUS_ADDRESS: int = 65535
MAX_MODBUS_COUNT: int = 125  # Registers per request (Modbus protocol practical limit)
MAX_COIL_COUNT: int = 2000  # Coils/discrete inputs per request


@dataclass(slots=True)
class ConnectionConfig:
    """Connection settings for Modbus TCP sessions."""

    ip: str
    port: int = DEFAULT_PORT
    unit: int = 1
    timeout: float = DEFAULT_TIMEOUT
    simulate: bool = False


@dataclass(slots=True)
class OperationResult:
    """Standardized operation output for human/JSON formatting."""

    ip: str
    unit: int
    function: str
    start: int
    count: int
    values: list[int | bool]
