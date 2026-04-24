# Cliente_MODBUS_PLC

Professional Python 3.11 command-line Modbus TCP client for OT cybersecurity diagnostics, lab testing, and safe parameter validation.

## Features

- Modbus TCP connection management (IP, port, unit/slave ID).
- Read operations:
  - Holding Registers
  - Input Registers
  - Coils
  - Discrete Inputs
- Write operations:
  - Single / multiple holding registers
  - Single / multiple coils
- Safety controls:
  - Write confirmation prompt
  - `--dry-run` mode
  - Address/range validation
- Output modes:
  - Human-readable console output
  - JSON output (`--output json`)
  - Optional CSV export (`--csv path.csv`)
- Logging:
  - INFO / DEBUG / ERROR
  - Optional JSON logs (`--json-logs`)
- Testing and simulation:
  - In-memory simulation mode (`--simulate`)
  - Local Modbus test server command (`start-sim-server`)
- Optional diagnostics enhancement:
  - Polling mode (`--poll-interval`, `--iterations`)

## Project structure

```
modbus_plc_client/
├── modbus_client.py
├── modbus_connection.py
├── modbus_reader.py
├── modbus_writer.py
├── config.py
├── logger.py
├── utils.py
├── requirements.txt
└── README.md
```

## Installation

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r modbus_plc_client/requirements.txt
```

## Usage examples

### Read holding registers

```bash
python modbus_plc_client/modbus_client.py read-holding \
  --ip 192.168.1.10 \
  --unit 1 \
  --start 0 \
  --count 10
```

### Read input registers (JSON output)

```bash
python modbus_plc_client/modbus_client.py read-input \
  --ip 192.168.1.10 \
  --unit 1 \
  --start 0 \
  --count 5 \
  --output json
```

### Read coils

```bash
python modbus_plc_client/modbus_client.py read-coils \
  --ip 192.168.1.10 \
  --unit 1 \
  --start 0 \
  --count 8
```

### Write single register (with confirmation)

```bash
python modbus_plc_client/modbus_client.py write-register \
  --ip 192.168.1.10 \
  --unit 1 \
  --address 5 \
  --value 123
```

### Write multiple registers (dry-run)

```bash
python modbus_plc_client/modbus_client.py write-registers \
  --ip 192.168.1.10 \
  --unit 1 \
  --address 20 \
  --values 10,20,30 \
  --dry-run \
  --yes
```

### Write coils in simulation mode

```bash
python modbus_plc_client/modbus_client.py write-coils \
  --ip 127.0.0.1 \
  --port 1502 \
  --unit 1 \
  --address 0 \
  --values 1,0,1,1 \
  --simulate \
  --yes
```

### Start local Modbus test server

```bash
python modbus_plc_client/modbus_client.py start-sim-server --ip 127.0.0.1 --port 1502
```

Then connect using read/write commands without `--simulate`.

## Security notes for OT labs

- Always use isolated lab networks before sending write operations.
- Use `--dry-run` first to verify intended writes.
- Keep `--yes` disabled during exploratory testing to enforce human confirmation.
- Prefer `--simulate` and local test server for pre-production validation.

## JSON result example

```json
{
  "ip": "192.168.1.10",
  "unit": 1,
  "function": "read_holding_registers",
  "start": 0,
  "count": 3,
  "values": [123, 456, 789]
}
```
