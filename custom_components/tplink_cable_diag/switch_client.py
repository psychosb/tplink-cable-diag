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

            # Read response in chunks until connection closes
            chunks = []
            try:
                while True:
                    chunk = await asyncio.wait_for(reader.read(4096), timeout=15)
                    if not chunk:
                        break
                    chunks.append(chunk)
            except asyncio.TimeoutError:
                pass

            resp = b"".join(chunks)
            text = resp.decode("utf-8", errors="replace")

            idx = text.find("\r\n\r\n")
            return text[idx + 4:] if idx > 0 else text

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

    def _parse_results(self, html: str) -> dict | None:
        """Parse cablestate and cablelength arrays from HTML response."""
        state_match = re.search(r'cablestate\s*=\s*\[([^\]]+)\]', html)
        length_match = re.search(r'cablelength\s*=\s*\[([^\]]+)\]', html)

        if not state_match:
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

    async def async_run_test(self, ports: list[int] | None = None) -> dict | None:
        """Run cable test on specified ports.

        Flow: login → trigger test CGI → wait → fetch results page.
        """
        if ports is None:
            ports = list(range(1, self.max_ports + 1))

        # Step 1: Login
        if not await self._async_login():
            return None

        await asyncio.sleep(0.5)

        # Step 2: Trigger the cable test
        params = "&".join(f"chk_{p}={p}" for p in ports) + "&Apply=Apply"
        trigger_resp = await self._async_http(f"/cable_diag_get.cgi?{params}")

        # The CGI might return results directly or require a separate fetch
        results = self._parse_results(trigger_resp)
        if results:
            # Check if any tested port has actual results (not all -1)
            has_data = any(
                results[p]["state"] != -1 for p in ports if p in results
            )
            if has_data:
                _LOGGER.debug("Got results directly from CGI response")
                return results

        # Step 3: Wait for test to complete
        _LOGGER.debug("Waiting for cable test to complete...")
        await asyncio.sleep(5)

        # Step 4: Fetch results from the diagnostics page
        # Need to login again (switch drops session after CGI call)
        if not await self._async_login():
            _LOGGER.error("Failed to re-login after cable test")
            return None

        await asyncio.sleep(0.5)

        results_page = await self._async_http("/CableDiagRpm.htm")
        if not results_page:
            _LOGGER.error("Failed to fetch cable test results page")
            return None

        results = self._parse_results(results_page)
        if results:
            has_data = any(
                results[p]["state"] != -1 for p in ports if p in results
            )
            if has_data:
                _LOGGER.debug("Got results from results page")
                return results

        _LOGGER.error(
            "Cable test completed but no results for tested ports (all -1). "
            "Response size: %d bytes", len(results_page),
        )
        return results  # Return anyway with -1 states rather than failing

    async def async_test_connection(self) -> bool:
        """Test if we can connect and login to the switch."""
        return await self._async_login()
