import asyncio
import os
import logging

import asyncssh
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load environment variables early
load_dotenv()

# Setup clean, visible logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - [%(levelname)s] - %(message)s"
)
logger = logging.getLogger("OpenWRT-MCP")

# Initialize FastMCP Server
mcp = FastMCP("OpenWRT-MCP")


# SSH Configuration from environment variables
OPENWRT_HOST = os.getenv("OPENWRT_HOST")
OPENWRT_USER = os.getenv("OPENWRT_USER")
OPENWRT_PASSWORD = os.getenv("OPENWRT_PASSWORD")
OPENWRT_KEY_PATH = os.getenv("OPENWRT_KEY_PATH")


async def run_ssh_command(command: str) -> str:
    """Helper to run a command over SSH."""
    if not OPENWRT_HOST:
        logger.error("SSH Execution aborted: OPENWRT_HOST is not configured.")
        return "Error: OPENWRT_HOST environment variable is not set. Please set OPENWRT_HOST to your router's IP."

    connect_kwargs = {
        "host": OPENWRT_HOST,
        "username": OPENWRT_USER,
        "known_hosts": None,  # Skip known hosts key verification for local router
        "login_timeout": 10,  # 10s timeout for initial connection
    }

    if OPENWRT_KEY_PATH and os.path.exists(OPENWRT_KEY_PATH):
        connect_kwargs["client_keys"] = [OPENWRT_KEY_PATH]
    if OPENWRT_PASSWORD:
        connect_kwargs["password"] = OPENWRT_PASSWORD

    if not OPENWRT_PASSWORD and not OPENWRT_KEY_PATH:
        logger.error(
            "SSH Execution aborted: Missing both password and key credentials."
        )
        return "Error: Neither OPENWRT_PASSWORD nor OPENWRT_KEY_PATH is set. Please set one for authenticating to the router."

    logger.info(f"Executing SSH command: '{command}' on target {OPENWRT_HOST}")

    try:
        # Run with overall timeout
        async with asyncio.timeout(60):
            async with asyncssh.connect(**connect_kwargs) as conn:
                result = await conn.run(command)
                if result.exit_status != 0:
                    error_msg = f"Command exited with status {result.exit_status}\n"
                    if result.stderr:
                        error_msg += f"Stderr: {result.stderr}\n"
                    if result.stdout:
                        error_msg += f"Stdout: {result.stdout}"

                    logger.warning(
                        f"Command execution failed (Code {result.exit_status})"
                    )
                    return error_msg

                logger.info("Command completed successfully.")
                return (
                    result.stdout
                    if result.stdout
                    else "Command executed successfully with no output."
                )
    except asyncio.TimeoutError:
        logger.error(f"Timeout reached: Command '{command}' exceeded 60 seconds limit.")
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        logger.error(f"SSH Session Failure: {str(e)}", exc_info=True)
        return f"SSH Connection Error: {str(e)}"


SENSITIVE_PATTERNS = [
    "reboot",
    "poweroff",
    "rm ",
    "uci set",
    "uci commit",
    "uci delete",
    "opkg ",
    "apk ",
    "wget",
    "curl",
    "sh ",
    "bash ",
    "ash ",
    "passwd",
    "firstboot",
]


@mcp.tool()
async def execute_command(command: str, confirmed: bool = False) -> str:
    """
    Execute a generic shell command on the OpenWRT router.
    Use this to run troubleshooting utilities like 'traceroute', 'ip addr', 'uci show', etc.
    Requires 'confirmed=True' for sensitive commands like 'reboot', 'rm', or 'uci set'.
    """
    logger.info(
        f"[TOOL TRIGGERED] execute_command | command='{command}', confirmed={confirmed}"
    )

    is_sensitive = any(pattern in command for pattern in SENSITIVE_PATTERNS)

    if is_sensitive and not confirmed:
        logger.warning(
            f"Blocked sensitive command execution attempt: '{command}' (confirmed=False)"
        )
        return (
            f"SENSITIVE COMMAND DETECTED: {command}\n\n"
            "This command could potentially disrupt your router's operation. "
            "To proceed, please confirm your intent by asking me to 'Confirm' or 'Proceed'."
        )

    return await run_ssh_command(command)


@mcp.tool()
async def read_router_logs(lines: int = 50) -> str:
    """
    Fetch the latest system logs from the OpenWRT router using 'logread'.
    """
    logger.info(f"[TOOL TRIGGERED] read_router_logs | lines={lines}")
    return await run_ssh_command(f"logread -l {lines}")


@mcp.tool()
async def ping_from_router(host: str, count: int = 4) -> str:
    """
    Execute a ping command from the OpenWRT router to an external host or IP to test connectivity.
    """
    logger.info(f"[TOOL TRIGGERED] ping_from_router | host='{host}', count={count}")
    return await run_ssh_command(f"ping -c {count} {host}")


@mcp.tool()
async def get_ubus_network_interfaces() -> str:
    """
    Get detailed network interfaces status from ubus.
    Returns structured data about all interfaces, including IP addresses, uptimes, loopback state, and tx/rx bytes.
    """
    logger.info("[TOOL TRIGGERED] get_ubus_network_interfaces")
    return await run_ssh_command("ubus call network.interface dump")


@mcp.tool()
async def get_ubus_wireless_status() -> str:
    """
    Get detailed wireless status from ubus.
    Useful for seeing radiophys, associated clients, signal strength, and noise configuration.
    """
    logger.info("[TOOL TRIGGERED] get_ubus_wireless_status")
    return await run_ssh_command("ubus call network.wireless status")


@mcp.tool()
async def get_dhcp_leases() -> str:
    """
    Parse and retrieve the currently connected local devices (DHCP leases) from the router.
    Returns rows of: MAC address, IP address, and Hostname for each connected device.
    """
    logger.info("[TOOL TRIGGERED] get_dhcp_leases")
    # Parse /tmp/dhcp.leases: [timestamp] [mac] [ip] [hostname] [clientid]
    script = 'cat /tmp/dhcp.leases | awk \'{print "IP: " $3 ", MAC: " $2 ", Hostname: " $4}\''
    return await run_ssh_command(script)


@mcp.tool()
async def run_speedtest() -> str:
    """
    Run a speed test from the OpenWRT router to check internet bandwidth.
    """
    logger.info("[TOOL TRIGGERED] run_speedtest")
    raw_output = await run_ssh_command("speedtest --output json")

    import json

    try:
        data = json.loads(raw_output.strip())
        client = data.get("client", {})
        client_ip = client.get("ip", "Unknown IP")
        client_isp = client.get("isp", "Unknown ISP")

        server = data.get("server", {})
        server_name = server.get("name", "Unknown Server")
        server_sponsor = server.get("sponsor", "Unknown Sponsor")
        server_dist = server.get("distance", "Unknown")

        ping = data.get("ping", "Unknown")
        jitter = data.get("jitter", "Unknown")

        download_mbit = data.get("download_mbit", "Unknown")
        upload_mbit = data.get("upload_mbit", "Unknown")

        summary = (
            "Speedtest Results:\n"
            "------------------\n"
            f"Client: {client_isp} ({client_ip})\n"
            f"Server: {server_name} - {server_sponsor} (Distance: {server_dist} km)\n"
            f"Ping: {ping} ms (Jitter: {jitter} ms)\n"
            f"Download: {download_mbit} Mbit/s\n"
            f"Upload: {upload_mbit} Mbit/s\n\n"
            "Raw Output:\n"
            f"{raw_output}"
        )
        return summary
    except Exception:
        return raw_output


@mcp.tool()
async def get_installed_software() -> str:
    """
    Retrieve the list of all installed software packages on the router using 'apk info'.
    """
    logger.info("[TOOL TRIGGERED] get_installed_software")
    return await run_ssh_command("apk info")


@mcp.tool()
async def install_software(package: str, confirmed: bool = False) -> str:
    """
    Install a software package on the router using 'apk add'.
    Requires 'confirmed=True' as package installation consumes router storage and bandwidth.
    """
    logger.info(
        f"[TOOL TRIGGERED] install_software | package='{package}', confirmed={confirmed}"
    )
    if not confirmed:
        return (
            f"WARNING: You are attempting to install the package '{package}'.\n"
            "This will consume router storage and bandwidth. "
            "To proceed, please set confirmed=True."
        )
    df_output = await run_ssh_command("df -k /")
    apk_output = await run_ssh_command(f"apk add {package}")
    return (
        f"Disk Space before install:\n{df_output}\n\nInstallation Output:\n{apk_output}"
    )


@mcp.tool()
async def get_context() -> str:
    """
    Get router context: OpenWRT version, CPU architecture/model, memory info, board model, uptime, and system load.
    """
    logger.info("[TOOL TRIGGERED] get_context")
    board_info = await run_ssh_command("ubus call system board")
    memory_info = await run_ssh_command("free -h")
    uptime_info = await run_ssh_command("uptime")
    cpu_info = await run_ssh_command(
        "grep -E 'model name|system type|machine' /proc/cpuinfo | uniq"
    )

    return (
        "Router System Context:\n"
        "======================\n"
        "--- Board & OS Info ---\n"
        f"{board_info}\n"
        "--- CPU Info ---\n"
        f"{cpu_info}\n"
        "--- Memory Usage ---\n"
        f"{memory_info}\n"
        "--- Uptime & Load ---\n"
        f"{uptime_info}\n"
    )


@mcp.tool()
async def get_routing_table() -> str:
    """
    Retrieve the active IPv4 and IPv6 routing tables from the router.
    Useful for diagnosing routing, gateway, and path issues.
    """
    logger.info("[TOOL TRIGGERED] get_routing_table")
    ipv4_routes = await run_ssh_command("ip route show")
    ipv6_routes = await run_ssh_command("ip -6 route show")
    return (
        "Routing Tables:\n"
        "===============\n"
        "--- IPv4 Routes ---\n"
        f"{ipv4_routes}\n\n"
        "--- IPv6 Routes ---\n"
        f"{ipv6_routes}\n"
    )


@mcp.tool()
async def get_firewall_rules() -> str:
    """
    Retrieve the configured firewall zones, redirects, and rules using UCI.
    """
    logger.info("[TOOL TRIGGERED] get_firewall_rules")
    return await run_ssh_command("uci show firewall")


@mcp.tool()
async def check_internet_connection() -> str:
    """
    Perform a comprehensive, high-level internet connectivity test from the router.
    Checks WAN IP gateway ping, external DNS resolution, and latency to common endpoints.
    """
    logger.info("[TOOL TRIGGERED] check_internet_connection")
    ping_ip = await run_ssh_command("ping -c 2 8.8.8.8")
    dns_res = await run_ssh_command("nslookup google.com")
    http_check = await run_ssh_command("wget -q -O- http://neverssl.com | head -n 5")

    return (
        "Internet Connectivity Diagnosis:\n"
        "================================\n"
        "--- Ping Test (8.8.8.8) ---\n"
        f"{ping_ip}\n\n"
        "--- DNS Resolution Test (google.com) ---\n"
        f"{dns_res}\n\n"
        "--- HTTP Access Test (neverssl.com) ---\n"
        f"{http_check}\n"
    )


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)  # nosec: B104
