# 🌐 OpenWRT MCP Server 🚀

A fast, asynchronous Model Context Protocol (MCP) server for inspecting and diagnosing OpenWRT routers.

Connect your LLMs and AI agents directly to your home network's backbone, giving them real-time visibility into interfaces, wireless status, system logs, DHCP leases, and generic shell execution via SSH.

---

## ✨ Features

- **Safe & Fast SSH Setup**: Connects asynchronously to your router; handles timeouts cleanly.
- **Built-in Diagnostics**: 
  - `read_router_logs(lines)`: Fetch system logs using `logread`.
  - `ping_from_router(host, count)`: Easily test connectivity starting from the router.
  - `get_ubus_network_interfaces()`: Dump structured interface data natively from `ubus`.
  - `get_ubus_wireless_status()`: Review radio stats, signal, and noise gracefully.
  - `get_dhcp_leases()`: Parses `/tmp/dhcp.leases` into readable MAC, IP, and Hostname info.
- **Generic Command Execution**: Run troubleshooting commands over SSH via `execute_command(command, confirmed)`.
- **Human-in-the-Loop (HITL)**: Protects against disruptive actions. Running sensitive commands (e.g., `reboot`, `rm`, or `uci` changes) without setting `confirmed=True` returns a warning prompt asking the agent/user to confirm and re-run the tool with the confirmation flag set to `True`.

## 📦 Prerequisites

- **Python 3.12+**
- A package manager like `uv` (recommended) or `pip`

## 🚀 Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/PiterPentester/openwrt_mcp.git
   cd openwrt_mcp
   ```

2. **Project dependencies:**
   Using `uv`, you can easily sync your dependencies:
   ```bash
   uv sync
   ```

## ⚙️ Configuration

Set the following environment variables before running the server so it knows how to authenticate against your router:

| Environment Variable | Description |
|----------------------|-------------|
| `OPENWRT_HOST`       | **Required.** The IP address or hostname of your OpenWRT router. |
| `OPENWRT_USER`       | The SSH user (defaults to `root` on OpenWRT). |
| `OPENWRT_PASSWORD`   | SSH password (if not using keys). |
| `OPENWRT_KEY_PATH`   | Path to an SSH private key for authentication. |

*You must set at least one of `OPENWRT_PASSWORD` or `OPENWRT_KEY_PATH`.*

## 💻 Usage

To use this with an MCP client (such as VS Code or your own agent), configure it to invoke the `main.py` entrypoint through `uv run`. 

For example, your client's MCP configuration might look like this:

```json
{
  "mcpServers": {
    "openwrt-diagnostic": {
      "command": "uv",
      "args": [
        "run",
        "/path/to/openwrt_mcp/main.py"
      ],
      "env": {
        "OPENWRT_HOST": "192.168.1.1",
        "OPENWRT_USER": "root",
        "OPENWRT_PASSWORD": "your_secure_password"
      }
    }
  }
}
```

## 🛠️ Built With

- **[FastMCP](https://github.com/jlowin/fastmcp)** - For rapid MCP server development.
- **[asyncssh](https://github.com/ronf/asyncssh)** - For asynchronous SSH connections.
