"""Write operations for Modbus objects, with safety controls."""

from __future__ import annotations

import logging

from modbus_connection import ModbusConnection
from utils import ensure_values_fit_range, validate_address


class ModbusWriter:
    """Implements validated write operations for registers and coils."""

    def __init__(self, connection: ModbusConnection, logger: logging.Logger) -> None:
        self.connection = connection
        self.logger = logger

    def write_single_register(self, address: int, value: int, dry_run: bool = False) -> str:
        validate_address(address)
        return self._write(
            function_name="write_register",
            address=address,
            values=[value],
            dry_run=dry_run,
        )

    def write_multiple_registers(
        self, address: int, values: list[int], dry_run: bool = False
    ) -> str:
        validate_address(address)
        ensure_values_fit_range(address, values)
        return self._write(
            function_name="write_registers",
            address=address,
            values=values,
            dry_run=dry_run,
        )

    def write_single_coil(self, address: int, value: bool, dry_run: bool = False) -> str:
        validate_address(address)
        return self._write(
            function_name="write_coil",
            address=address,
            values=[value],
            dry_run=dry_run,
        )

    def write_multiple_coils(
        self, address: int, values: list[bool], dry_run: bool = False
    ) -> str:
        validate_address(address)
        ensure_values_fit_range(address, values)
        return self._write(
            function_name="write_coils",
            address=address,
            values=values,
            dry_run=dry_run,
        )

    def _write(
        self,
        function_name: str,
        address: int,
        values: list[int | bool],
        dry_run: bool,
    ) -> str:
        self.logger.info(
            "Preparing write operation.",
            extra={
                "context": {
                    "function": function_name,
                    "address": address,
                    "values": values,
                    "dry_run": dry_run,
                }
            },
        )

        if dry_run:
            return f"DRY-RUN: {function_name} would write {values} at address {address}."

        if self.connection.config.simulate:
            self._write_simulated(function_name, address, values)
            return f"SIMULATION: {function_name} wrote {values} at address {address}."

        if self.connection.client is None:
            raise ConnectionError("Modbus client is not connected.")

        client = self.connection.client
        unit = self.connection.config.unit

        if function_name == "write_register":
            response = client.write_register(address=address, value=int(values[0]), slave=unit)
        elif function_name == "write_registers":
            response = client.write_registers(address=address, values=[int(v) for v in values], slave=unit)
        elif function_name == "write_coil":
            response = client.write_coil(address=address, value=bool(values[0]), slave=unit)
        elif function_name == "write_coils":
            response = client.write_coils(address=address, values=[bool(v) for v in values], slave=unit)
        else:
            raise ValueError(f"Unsupported write function: {function_name}")

        if response.isError():
            raise RuntimeError(f"Write failed: {response}")

        return f"OK: {function_name} wrote {values} at address {address}."

    def _write_simulated(self, function_name: str, address: int, values: list[int | bool]) -> None:
        assert self.connection.simulated_store is not None
        store = self.connection.simulated_store

        if function_name in {"write_register", "write_registers"}:
            for offset, value in enumerate(values):
                store.holding_registers[address + offset] = int(value)
            return

        if function_name in {"write_coil", "write_coils"}:
            for offset, value in enumerate(values):
                store.coils[address + offset] = bool(value)
            return

        raise ValueError(f"Unsupported simulated write function: {function_name}")
