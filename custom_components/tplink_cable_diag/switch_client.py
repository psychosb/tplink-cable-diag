"""Client for communicating with TP-Link TL-SG108E web interface."""

import asyncio
import logging
import re
import socket

_LOGGER = logging.getLogger(__name__)

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


class TpLinkSwitchClient:
    """Client to interact with TL-SG108E web interface for cable diagnostics."""

    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password
        self.max_ports = 8

    def _raw_http(self, path: str, body: str | None = None) -> str:
        """Send raw HTTP request to the switch (sync, runs in executor)."""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(15)
        try:
            s.connect((self.host, 80))
            method = "POST" if body else "GET"
            req = (
                f"{method} {path} HTTP/1.0\r\n"
                f"Host: {self.host}\r\n"
                f"Referer: http://{self.host}/CableDiagRpm.htm\r\n"
            )
            if body:
                req += (
                    f"Content-Type: application/x-www-form-urlencoded\r\n"
                    f"Content-Length: {len(body)}\r\n"
                )
            req += "Connection: close\r\n\r\n"
            if body:
                req += body
            s.sendall(req.encode())
            resp = b""
            while True:
                try:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    resp += chunk
                except socket.timeout:
                    break
            text = resp.decode("utf-8", errors="replace")
            idx = text.find("\r\n\r\n")
            return text[idx + 4:] if idx > 0 else text
        except Exception as e:
            _LOGGER.error("Failed to communicate with switch at %s: %s", self.host, e)
            return ""
        finally:
            s.close()

    def _login(self) -> bool:
        """Login to the switch."""
        resp = self._raw_http(
            "/logon.cgi",
            f"username={self.username}&password={self.password}&logon=Login",
        )
        err = re.search(r'logonInfo\s*=\s*new\s+Array\(\s*(\d+)', resp)
        if err and err.group(1) == "0":
            return True
        _LOGGER.error("Switch login failed (errType=%s)", err.group(1) if err else "unknown")
        return False

    def _run_test(self, ports: list[int]) -> dict | None:
        """Run cable test on specified ports (blocking)."""
        import time

        if not self._login():
            return None

        time.sleep(0.5)

        params = "&".join(f"chk_{p}={p}" for p in ports) + "&Apply=Apply"
        result = self._raw_http(f"/cable_diag_get.cgi?{params}")

        if not result:
            return None

        state_match = re.search(r'cablestate\s*=\s*\[([^\]]+)\]', result)
        length_match = re.search(r'cablelength\s*=\s*\[([^\]]+)\]', result)

        if not state_match:
            _LOGGER.error("Failed to parse cable test results")
            return None

        states = [int(x.strip()) for x in state_match.group(1).split(",")]
        lengths = (
            [int(x.strip()) for x in length_match.group(1).split(",")]
            if length_match
            else [-1] * self.max_ports
        )

        port_results = {}
        for i in range(self.max_ports):
            port_num = i + 1
            port_results[port_num] = {
                "state": states[i],
                "state_name": STATE_NAMES.get(states[i], f"Unknown({states[i]})"),
                "length_m": lengths[i] if lengths[i] >= 0 else None,
                "fault": states[i] in FAULT_STATES,
            }

        return port_results

    async def async_run_test(
        self, ports: list[int] | None = None
    ) -> dict | None:
        """Run cable test asynchronously."""
        if ports is None:
            ports = list(range(1, self.max_ports + 1))
        return await asyncio.get_event_loop().run_in_executor(
            None, self._run_test, ports
        )

    async def async_test_connection(self) -> bool:
        """Test if we can connect and login to the switch."""
        return await asyncio.get_event_loop().run_in_executor(None, self._login)
