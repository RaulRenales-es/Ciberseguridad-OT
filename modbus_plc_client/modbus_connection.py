"""Connection lifecycle management for Modbus TCP, including simulation mode."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from pymodbus.client import ModbusTcpClient

from config import ConnectionConfig


@dataclass(slots=True)
class SimulatedDataStore:
    """In-memory data store used for simulation mode and dry testing."""

    holding_registers: dict[int, int] = field(default_factory=lambda: {i: i * 10 for i in range(0, 50)})
    input_registers: dict[int, int] = field(default_factory=lambda: {i: i * 5 for i in range(0, 50)})
    coils: dict[int, bool] = field(default_factory=lambda: {i: (i % 2 == 0) for i in range(0, 50)})
    discrete_inputs: dict[int, bool] = field(
        default_factory=lambda: {i: (i % 3 == 0) for i in range(0, 50)}
    )


class ModbusConnection:
    """Wrapper around pymodbus TCP client with safe connect/close lifecycle."""

    def __init__(self, config: ConnectionConfig, logger: logging.Logger) -> None:
        self.config = config
        self.logger = logger
        self.client: ModbusTcpClient | None = None
        self.simulated_store: SimulatedDataStore | None = None

    def connect(self) -> None:
        """Open a Modbus TCP connection or initialize simulation backend."""

        if self.config.simulate:
            self.simulated_store = SimulatedDataStore()
            self.logger.info(
                "Simulation mode enabled; using in-memory Modbus test registers.",
                extra={"context": {"ip": self.config.ip, "port": self.config.port}},
            )
            return

        self.logger.info(
            "Connecting to Modbus TCP server.",
            extra={
                "context": {
                    "ip": self.config.ip,
                    "port": self.config.port,
                    "unit": self.config.unit,
                    "timeout": self.config.timeout,
                }
            },
        )

        self.client = ModbusTcpClient(
            host=self.config.ip,
            port=self.config.port,
            timeout=self.config.timeout,
        )
        ok = self.client.connect()
        if not ok:
            raise ConnectionError(
                f"Failed to connect to {self.config.ip}:{self.config.port}."
            )

        self.logger.info(f"Connected to {self.config.ip}:{self.config.port}")

    def close(self) -> None:
        """Close TCP client if open."""

        if self.client is not None:
            self.client.close()
            self.logger.info("Connection closed.")

    def __enter__(self) -> "ModbusConnection":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
