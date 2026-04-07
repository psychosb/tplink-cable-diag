"""Client for communicating with TP-Link TL-SG108E web interface."""

import asyncio
import logging
import re

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

    async def _async_http(self, path: str, body: str | None = None) -> str:
        """Send raw HTTP request using asyncio streams."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, 80),
                timeout=10,
            )
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout connecting to switch at %s:80", self.host)
            return ""
        except ConnectionRefusedError:
            _LOGGER.error("Connection refused by switch at %s:80", self.host)
            return ""
        except OSError as e:
            _LOGGER.error("Network error connecting to switch at %s:80 - %s", self.host, e)
            return ""

        try:
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

            writer.write(req.encode())
            await writer.drain()

            resp = await asyncio.wait_for(reader.read(65536), timeout=15)
            text = resp.decode("utf-8", errors="replace")

            idx = text.find("\r\n\r\n")
            return text[idx + 4:] if idx > 0 else text

        except asyncio.TimeoutError:
            _LOGGER.error("Timeout reading response from switch at %s", self.host)
            return ""
        except Exception as e:
            _LOGGER.error(
                "Error communicating with switch at %s: %s (%s)",
                self.host, e, type(e).__name__,
            )
            return ""
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _async_login(self) -> bool:
        """Login to the switch."""
        _LOGGER.debug("Attempting login to switch at %s", self.host)
        resp = await self._async_http(
            "/logon.cgi",
            f"username={self.username}&password={self.password}&logon=Login",
        )
        if not resp:
            _LOGGER.error("Switch at %s returned empty response on login", self.host)
            return False
        err = re.search(r'logonInfo\s*=\s*new\s+Array\(\s*(\d+)', resp)
        if err and err.group(1) == "0":
            _LOGGER.debug("Login successful to switch at %s", self.host)
            return True
        _LOGGER.error(
            "Switch login failed at %s (errType=%s, response_size=%d)",
            self.host,
            err.group(1) if err else "unknown",
            len(resp),
        )
        return False

    async def async_run_test(self, ports: list[int] | None = None) -> dict | None:
        """Run cable test on specified ports."""
        if ports is None:
            ports = list(range(1, self.max_ports + 1))

        if not await self._async_login():
            return None

        await asyncio.sleep(0.5)

        params = "&".join(f"chk_{p}={p}" for p in ports) + "&Apply=Apply"
        result = await self._async_http(f"/cable_diag_get.cgi?{params}")

        if not result:
            _LOGGER.error("Cable test returned empty response")
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

    async def async_test_connection(self) -> bool:
        """Test if we can connect and login to the switch."""
        return await self._async_login()
