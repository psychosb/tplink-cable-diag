"""Constants for TP-Link Cable Diagnostics integration."""

DOMAIN = "tplink_cable_diag"

CONF_SWITCH_IP = "switch_ip"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 360  # 6 hours in minutes

STATE_NAMES = {
    0: "No Cable",
    1: "Normal",
    2: "Open",
    3: "Short",
    4: "Open & Short",
    5: "Cross Cable",
    -1: "Not tested",
}

FAULT_STATES = {2, 3, 4, 5}
