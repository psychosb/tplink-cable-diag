"""Constants for TP-Link Cable Diagnostics integration."""

DOMAIN = "tplink_cable_diag"

CONF_SWITCH_IP = "switch_ip"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SCHEDULE_DAY = "schedule_day"
CONF_SCHEDULE_HOUR = "schedule_hour"

DEFAULT_USERNAME = "admin"
DEFAULT_SCAN_INTERVAL = 0  # 0 = use schedule instead of interval
DEFAULT_SCHEDULE_DAY = "daily"
DEFAULT_SCHEDULE_HOUR = 6  # 6 AM

SCHEDULE_DAYS = ["daily", "mon", "tue", "wed", "thu", "fri", "sat", "sun"]

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
