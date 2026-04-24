"""Read operations for Modbus objects."""

from __future__ import annotations

import logging

from config import OperationResult
from modbus_connection import ModbusConnection
from utils import validate_range


class ModbusReader:
    """Implements safe and validated Modbus read operations."""

    def __init__(self, connection: ModbusConnection, logger: logging.Logger) -> None:
        self.connection = connection
        self.logger = logger

    def read_holding(self, start: int, count: int) -> OperationResult:
        start, count = validate_range(start, count, is_coil=False)
        return self._read("read_holding_registers", start, count)

    def read_input(self, start: int, count: int) -> OperationResult:
        start, count = validate_range(start, count, is_coil=False)
        return self._read("read_input_registers", start, count)

    def read_coils(self, start: int, count: int) -> OperationResult:
        start, count = validate_range(start, count, is_coil=True)
        return self._read("read_coils", start, count)

    def read_discrete(self, start: int, count: int) -> OperationResult:
        start, count = validate_range(start, count, is_coil=True)
        return self._read("read_discrete_inputs", start, count)

    def _read(self, function_name: str, start: int, count: int) -> OperationResult:
        self.logger.info(
            "Executing read operation.",
            extra={"context": {"function": function_name, "start": start, "count": count}},
        )

        if self.connection.config.simulate:
            values = self._read_simulated(function_name, start, count)
        else:
            if self.connection.client is None:
                raise ConnectionError("Modbus client is not connected.")

            func = getattr(self.connection.client, function_name)
            response = func(address=start, count=count, slave=self.connection.config.unit)
            if response.isError():
                raise RuntimeError(f"Invalid response for {function_name}: {response}")
            values = getattr(response, "registers", None)
            if values is None:
                values = getattr(response, "bits", None)
            if values is None:
                raise RuntimeError("Response payload did not include registers/bits.")
            values = list(values[:count])

        return OperationResult(
            ip=self.connection.config.ip,
            unit=self.connection.config.unit,
            function=function_name,
            start=start,
            count=count,
            values=values,
        )

    def _read_simulated(self, function_name: str, start: int, count: int) -> list[int | bool]:
        assert self.connection.simulated_store is not None
        store = self.connection.simulated_store

        if function_name == "read_holding_registers":
            return [store.holding_registers.get(i, 0) for i in range(start, start + count)]
        if function_name == "read_input_registers":
            return [store.input_registers.get(i, 0) for i in range(start, start + count)]
        if function_name == "read_coils":
            return [store.coils.get(i, False) for i in range(start, start + count)]
        if function_name == "read_discrete_inputs":
            return [store.discrete_inputs.get(i, False) for i in range(start, start + count)]

        raise ValueError(f"Unsupported simulated read function: {function_name}")
