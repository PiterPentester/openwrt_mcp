import os
import asyncio
import asyncssh
from mcp.server.fastmcp import FastMCP

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
        return "Error: Neither OPENWRT_PASSWORD nor OPENWRT_KEY_PATH is set. Please set one for authenticating to the router."

    try:
        # Run with overall timeout
        async with asyncio.timeout(30):
            async with asyncssh.connect(**connect_kwargs) as conn:
                result = await conn.run(command)
                if result.exit_status != 0:
                    error_msg = f"Command exited with status {result.exit_status}\n"
                    if result.stderr:
                        error_msg += f"Stderr: {result.stderr}\n"
                    if result.stdout:
                        error_msg += f"Stdout: {result.stdout}"
                    return error_msg
                return (
                    result.stdout
                    if result.stdout
                    else "Command executed successfully with no output."
                )
    except asyncio.TimeoutError:
        return "Error: Command timed out after 30 seconds."
    except Exception as e:
        return f"SSH Connection Error: {str(e)}"


@mcp.tool()
async def execute_command(command: str) -> str:
    """
    Execute a generic shell command on the OpenWRT router.
    Use this to run troubleshooting utilities like 'traceroute', 'ip addr', 'uci show', etc.
    """
    return await run_ssh_command(command)


@mcp.tool()
async def read_router_logs(lines: int = 50) -> str:
    """
    Fetch the latest system logs from the OpenWRT router using 'logread'.
    """
    return await run_ssh_command(f"logread -l {lines}")


@mcp.tool()
async def ping_from_router(host: str, count: int = 4) -> str:
    """
    Execute a ping command from the OpenWRT router to an external host or IP to test connectivity.
    """
    return await run_ssh_command(f"ping -c {count} {host}")


@mcp.tool()
async def get_ubus_network_interfaces() -> str:
    """
    Get detailed network interfaces status from ubus.
    Returns structured data about all interfaces, including IP addresses, uptimes, loopback state, and tx/rx bytes.
    """
    return await run_ssh_command("ubus call network.interface dump")


@mcp.tool()
async def get_ubus_wireless_status() -> str:
    """
    Get detailed wireless status from ubus.
    Useful for seeing radiophys, associated clients, signal strength, and noise configuration.
    """
    return await run_ssh_command("ubus call network.wireless status")


@mcp.tool()
async def get_dhcp_leases() -> str:
    """
    Parse and retrieve the currently connected local devices (DHCP leases) from the router.
    Returns rows of: MAC address, IP address, and Hostname for each connected device.
    """
    # Parse /tmp/dhcp.leases: [timestamp] [mac] [ip] [hostname] [clientid]
    script = 'cat /tmp/dhcp.leases | awk \'{print "IP: " $3 ", MAC: " $2 ", Hostname: " $4}\''
    return await run_ssh_command(script)


if __name__ == "__main__":
    # Initialize and run via standard I/O (default for MCP)
    mcp.run(transport="stdio")
