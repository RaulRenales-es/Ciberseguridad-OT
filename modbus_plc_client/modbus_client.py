"""CLI entrypoint for Cliente_MODBUS_PLC."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import asdict
from typing import Any

from pymodbus.datastore import ModbusDeviceContext, ModbusSequentialDataBlock, ModbusServerContext
from pymodbus.server import StartTcpServer

from config import ConnectionConfig, DEFAULT_PORT
from logger import setup_logger
from modbus_connection import ModbusConnection
from modbus_reader import ModbusReader
from modbus_writer import ModbusWriter
from utils import (
    ValidationError,
    parse_bool_list,
    parse_int_list,
    validate_ip,
    validate_unit,
)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser and subcommands."""

    parser = argparse.ArgumentParser(
        description="Cliente_MODBUS_PLC - OT Modbus TCP diagnostic and test client"
    )
    parser.add_argument("--log-level", default="INFO", choices=["INFO", "DEBUG", "ERROR"])
    parser.add_argument("--json-logs", action="store_true", help="Emit logs in JSON format")

    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_conn_args(cmd: argparse.ArgumentParser) -> None:
        cmd.add_argument("--ip", required=True, help="Target PLC IP address")
        cmd.add_argument("--port", type=int, default=DEFAULT_PORT, help="Target TCP port")
        cmd.add_argument("--unit", type=int, default=1, help="Modbus unit/slave ID")
        cmd.add_argument("--timeout", type=float, default=3.0, help="Socket timeout in seconds")
        cmd.add_argument("--simulate", action="store_true", help="Use local in-memory simulation mode")
        cmd.add_argument("--output", choices=["console", "json"], default="console")
        cmd.add_argument("--csv", help="Optional CSV export path")
        cmd.add_argument(
            "--poll-interval",
            type=float,
            default=0.0,
            help="Continuous polling interval in seconds (0 disables)",
        )
        cmd.add_argument("--iterations", type=int, default=1, help="Number of poll cycles")

    read_holding = subparsers.add_parser("read-holding", help="Read holding registers")
    add_conn_args(read_holding)
    read_holding.add_argument("--start", type=int, required=True)
    read_holding.add_argument("--count", type=int, required=True)

    read_input = subparsers.add_parser("read-input", help="Read input registers")
    add_conn_args(read_input)
    read_input.add_argument("--start", type=int, required=True)
    read_input.add_argument("--count", type=int, required=True)

    read_coils = subparsers.add_parser("read-coils", help="Read coils")
    add_conn_args(read_coils)
    read_coils.add_argument("--start", type=int, required=True)
    read_coils.add_argument("--count", type=int, required=True)

    read_discrete = subparsers.add_parser("read-discrete", help="Read discrete inputs")
    add_conn_args(read_discrete)
    read_discrete.add_argument("--start", type=int, required=True)
    read_discrete.add_argument("--count", type=int, required=True)

    write_reg = subparsers.add_parser("write-register", help="Write single holding register")
    add_conn_args(write_reg)
    write_reg.add_argument("--address", type=int, required=True)
    write_reg.add_argument("--value", type=int, required=True)
    write_reg.add_argument("--dry-run", action="store_true")
    write_reg.add_argument("--yes", action="store_true", help="Skip confirmation prompt")

    write_regs = subparsers.add_parser("write-registers", help="Write multiple holding registers")
    add_conn_args(write_regs)
    write_regs.add_argument("--address", type=int, required=True)
    write_regs.add_argument("--values", required=True, help="Comma-separated values, e.g. 10,20,30")
    write_regs.add_argument("--dry-run", action="store_true")
    write_regs.add_argument("--yes", action="store_true", help="Skip confirmation prompt")

    write_coil = subparsers.add_parser("write-coil", help="Write single coil")
    add_conn_args(write_coil)
    write_coil.add_argument("--address", type=int, required=True)
    write_coil.add_argument("--value", required=True, choices=["1", "0", "true", "false"])
    write_coil.add_argument("--dry-run", action="store_true")
    write_coil.add_argument("--yes", action="store_true", help="Skip confirmation prompt")

    write_coils = subparsers.add_parser("write-coils", help="Write multiple coils")
    add_conn_args(write_coils)
    write_coils.add_argument("--address", type=int, required=True)
    write_coils.add_argument("--values", required=True, help="Comma-separated booleans: 1,0,true")
    write_coils.add_argument("--dry-run", action="store_true")
    write_coils.add_argument("--yes", action="store_true", help="Skip confirmation prompt")

    sim_server = subparsers.add_parser("start-sim-server", help="Start local Modbus TCP test server")
    sim_server.add_argument("--ip", default="127.0.0.1")
    sim_server.add_argument("--port", type=int, default=1502)

    return parser


def must_confirm(args: argparse.Namespace) -> bool:
    """Prompt user for explicit write confirmation unless --yes or --dry-run."""

    if getattr(args, "dry_run", False) or getattr(args, "yes", False):
        return True

    answer = input("WARNING: Write operation can affect PLC state. Continue? [y/N]: ")
    return answer.strip().lower() in {"y", "yes"}


def output_result(args: argparse.Namespace, payload: dict[str, Any]) -> None:
    """Render result payload to console or JSON."""

    if args.output == "json":
        print(json.dumps(payload, indent=2))
    else:
        print(f"[INFO] Connected to {payload['ip']}:{args.port}")
        print(f"[INFO] {payload['function']}")
        for offset, value in enumerate(payload["values"]):
            print(f"Address {payload['start'] + offset}: {value}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["address", "value"])
            for offset, value in enumerate(payload["values"]):
                writer.writerow([payload["start"] + offset, value])


def run_read(args: argparse.Namespace, logger) -> int:
    """Execute read command(s), including optional polling mode."""

    config = ConnectionConfig(
        ip=validate_ip(args.ip),
        port=args.port,
        unit=validate_unit(args.unit),
        timeout=args.timeout,
        simulate=args.simulate,
    )

    with ModbusConnection(config, logger) as conn:
        reader = ModbusReader(conn, logger)

        for iteration in range(args.iterations):
            if args.command == "read-holding":
                result = reader.read_holding(args.start, args.count)
            elif args.command == "read-input":
                result = reader.read_input(args.start, args.count)
            elif args.command == "read-coils":
                result = reader.read_coils(args.start, args.count)
            elif args.command == "read-discrete":
                result = reader.read_discrete(args.start, args.count)
            else:
                raise ValueError(f"Unsupported read command: {args.command}")

            payload = asdict(result)
            payload["poll_iteration"] = iteration + 1
            output_result(args, payload)

            if args.poll_interval > 0 and iteration < args.iterations - 1:
                time.sleep(args.poll_interval)

    return 0


def run_write(args: argparse.Namespace, logger) -> int:
    """Execute write commands with safety controls."""

    config = ConnectionConfig(
        ip=validate_ip(args.ip),
        port=args.port,
        unit=validate_unit(args.unit),
        timeout=args.timeout,
        simulate=args.simulate,
    )

    with ModbusConnection(config, logger) as conn:
        writer = ModbusWriter(conn, logger)

        if not must_confirm(args):
            print("Write cancelled by user.")
            return 1

        if args.command == "write-register":
            message = writer.write_single_register(args.address, args.value, dry_run=args.dry_run)
        elif args.command == "write-registers":
            message = writer.write_multiple_registers(
                args.address,
                parse_int_list(args.values),
                dry_run=args.dry_run,
            )
        elif args.command == "write-coil":
            parsed = parse_bool_list(args.value)
            if len(parsed) != 1:
                raise ValidationError("Single coil write requires exactly one boolean value.")
            message = writer.write_single_coil(args.address, parsed[0], dry_run=args.dry_run)
        elif args.command == "write-coils":
            message = writer.write_multiple_coils(
                args.address,
                parse_bool_list(args.values),
                dry_run=args.dry_run,
            )
        else:
            raise ValueError(f"Unsupported write command: {args.command}")

        print(message)
    return 0


def run_sim_server(args: argparse.Namespace, logger) -> int:
    """Start a local Modbus TCP simulation server with sample data blocks."""

    logger.info("Starting local Modbus simulation server", extra={"context": {"ip": args.ip, "port": args.port}})
    store = ModbusDeviceContext(
        di=ModbusSequentialDataBlock(0, [1] * 100),
        co=ModbusSequentialDataBlock(0, [0, 1] * 50),
        hr=ModbusSequentialDataBlock(0, list(range(100))),
        ir=ModbusSequentialDataBlock(0, [value * 2 for value in range(100)]),
    )
    context = ModbusServerContext(devices={1: store}, single=False)
    StartTcpServer(context=context, address=(args.ip, args.port))
    return 0


def main() -> int:
    """Program entrypoint."""

    parser = build_parser()
    args = parser.parse_args()
    logger = setup_logger(level=args.log_level, json_logs=args.json_logs)

    try:
        if args.command.startswith("read-"):
            return run_read(args, logger)
        if args.command.startswith("write-"):
            return run_write(args, logger)
        if args.command == "start-sim-server":
            return run_sim_server(args, logger)

        parser.error("Unknown command.")
        return 2
    except (ValidationError, ConnectionError, TimeoutError, RuntimeError, OSError) as exc:
        logger.error(f"Operation failed: {exc}")
        return 1
    except KeyboardInterrupt:
        logger.error("Interrupted by user.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
