# TP-Link Cable Diagnostics for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that runs cable diagnostics on TP-Link Easy Smart switches (TL-SG108E, TL-SG105E, etc.) and reports cable faults as sensors.

## Features

- **Per-port cable diagnostics** — sensors for each switch port showing cable status (Normal, Open, Short, Open & Short, Cross Cable, No Cable)
- **Fault detection** — binary sensor that turns ON when any port has a cable fault
- **Fault distance** — reports the distance (in meters) to the cable fault
- **Configurable scan interval** — set how often to run diagnostics (default: every 6 hours)
- **UI configuration** — full config flow, no YAML needed

## Supported Devices

- TP-Link TL-SG108E (tested)
- TP-Link TL-SG105E (should work)
- Other TP-Link Easy Smart switches with web interface cable diagnostics

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu (top right) → **Custom repositories**
3. Add this repository URL with category **Integration**
4. Search for "TP-Link Cable Diagnostics" and install
5. Restart Home Assistant

### Manual

1. Copy the `custom_components/tplink_cable_diag` folder to your HA `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for "TP-Link Cable Diagnostics"
3. Enter your switch's IP address, username, and password
4. Set the scan interval (30-1440 minutes, default 360 = 6 hours)

## Entities Created

### Sensors (one per port)

| Entity | State | Attributes |
|--------|-------|------------|
| `sensor.tl_sg108e_port_N_cable` | Normal / Open / Short / Open & Short / Cross Cable / No Cable | `port`, `fault`, `cable_length_m`, `fault_distance_m` |

### Binary Sensor

| Entity | State | Attributes |
|--------|-------|------------|
| `binary_sensor.tl_sg108e_cable_fault` | ON if any fault | `faulted_ports`, `fault_count` |

## Example Automation

Send a notification when a cable fault is detected:

```yaml
automation:
  - alias: "Network - Cable Fault Alert"
    triggers:
      - entity_id: binary_sensor.tl_sg108e_cable_fault
        to: "on"
        trigger: state
    actions:
      - action: notify.pushover
        data:
          title: "Network: Cable Fault Detected"
          message: >-
            Cable fault on TL-SG108E:
            {% for fault in state_attr('binary_sensor.tl_sg108e_cable_fault', 'faulted_ports') %}
            Port {{ fault.port }}: {{ fault.status }}{% if fault.distance_m is defined %} at {{ fault.distance_m }}m{% endif %}
            {% endfor %}
```

## How It Works

The integration communicates with the switch's web interface (HTTP) to:
1. Login with your credentials
2. Trigger the built-in cable diagnostic test
3. Parse the results (state and fault distance per port)

It uses the switch's own TDR (Time Domain Reflectometry) hardware to detect cable faults — the same test you can run manually from the switch's web UI under Monitoring → Cable Test.

**Note:** The cable test briefly disrupts the tested port (~1 second). The integration tests ports individually to minimize impact on active connections.

## Known Limitations

- The switch's web server only handles one session at a time
- Cable test results are point-in-time (not continuous monitoring)
- Scan intervals shorter than 30 minutes are not recommended

## License

MIT
