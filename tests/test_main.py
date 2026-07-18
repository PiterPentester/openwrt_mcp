import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import main


@pytest.fixture(autouse=True)
def setup_main_vars():
    main.OPENWRT_HOST = "192.168.1.1"
    main.OPENWRT_USER = "root"
    main.OPENWRT_PASSWORD = "password"
    main.OPENWRT_KEY_PATH = None


@pytest.mark.asyncio
async def test_run_ssh_command_success():
    with patch("main.asyncssh.connect", new_callable=MagicMock) as mock_connect:
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.exit_status = 0
        mock_result.stdout = "Hello World"
        mock_conn.run = AsyncMock(return_value=mock_result)

        # asyncssh.connect returns an object that works with 'async with'
        mock_connect.return_value.__aenter__.return_value = mock_conn

        result = await main.run_ssh_command("echo Hello World")
        assert result == "Hello World"
        mock_conn.run.assert_called_once_with("echo Hello World")


@pytest.mark.asyncio
async def test_run_ssh_command_failure():
    with patch("main.asyncssh.connect", new_callable=MagicMock) as mock_connect:
        mock_conn = AsyncMock()
        mock_result = MagicMock()
        mock_result.exit_status = 1
        mock_result.stdout = ""
        mock_result.stderr = "Command not found"
        mock_conn.run = AsyncMock(return_value=mock_result)

        mock_connect.return_value.__aenter__.return_value = mock_conn

        result = await main.run_ssh_command("badcmd")
        assert "Command exited with status 1" in result
        assert "Stderr: Command not found" in result


@pytest.mark.asyncio
async def test_run_ssh_command_no_host():
    main.OPENWRT_HOST = None
    result = await main.run_ssh_command("echo test")
    assert "OPENWRT_HOST environment variable is not set" in result


@pytest.mark.asyncio
async def test_execute_command():
    with patch("main.run_ssh_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = "traceroute output"
        res = await main.execute_command("traceroute 8.8.8.8")
        assert res == "traceroute output"
        mock_run.assert_called_once_with("traceroute 8.8.8.8")


@pytest.mark.asyncio
async def test_execute_command_sensitive():
    with patch("main.run_ssh_command", new_callable=AsyncMock) as mock_run:
        # Test sensitive command without confirmation
        res = await main.execute_command("reboot")
        assert "SENSITIVE COMMAND DETECTED" in res
        mock_run.assert_not_called()

        # Test sensitive command with confirmation
        mock_run.return_value = "rebooting"
        res = await main.execute_command("reboot", confirmed=True)
        assert res == "rebooting"
        mock_run.assert_called_once_with("reboot")


@pytest.mark.asyncio
async def test_read_router_logs():
    with patch("main.run_ssh_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = "logs"
        res = await main.read_router_logs(10)
        assert res == "logs"
        mock_run.assert_called_once_with("logread -l 10")


@pytest.mark.asyncio
async def test_run_speedtest_success():
    mock_json = '{"client":{"ip":"37.54.222.25","lat":"50.458","lon":"30.5303","isp":"JSC Ukrtelecom"},"servers_online":10,"server":{"name":"Zhytomyr","id":50234,"sponsor":"MYLAN ISP","distance":7,"latency":8,"host":"speedtest.internet.zt.ua.prod.hosts.ooklaserver.net:8080","recommended":0},"ping":8,"jitter":0,"download":428727482.12,"download_mbit":428.73,"upload":464589085.05,"upload_mbit":464.59,"_":"all ok"}'
    with patch("main.run_ssh_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = mock_json
        res = await main.run_speedtest()

        assert "37.54.222.25" in res
        assert "JSC Ukrtelecom" in res
        assert "Zhytomyr" in res
        assert "428.73" in res
        assert "464.59" in res
        assert "8" in res
        mock_run.assert_called_once_with("speedtest --output json")


@pytest.mark.asyncio
async def test_run_speedtest_non_json_fallback():
    with patch("main.run_ssh_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = "speedtest: command not found"
        res = await main.run_speedtest()
        assert res == "speedtest: command not found"
        mock_run.assert_called_once_with("speedtest --output json")


@pytest.mark.asyncio
async def test_get_installed_software():
    with patch("main.run_ssh_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = "libc\nbusybox\ndnsmasq"
        res = await main.get_installed_software()
        assert "libc" in res
        assert "busybox" in res
        assert "dnsmasq" in res
        mock_run.assert_called_once_with("apk info")


@pytest.mark.asyncio
async def test_install_software_no_confirm():
    with patch("main.run_ssh_command", new_callable=AsyncMock) as mock_run:
        res = await main.install_software("tcpdump")
        assert "WARNING: You are attempting to install" in res
        assert "confirmed=True" in res
        mock_run.assert_not_called()


@pytest.mark.asyncio
async def test_install_software_confirmed():
    with patch("main.run_ssh_command", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = ["df output", "OK installed tcpdump"]
        res = await main.install_software("tcpdump", confirmed=True)
        assert "df output" in res
        assert "OK installed tcpdump" in res
        mock_run.assert_any_call("df -k /")
        mock_run.assert_any_call("apk add tcpdump")


@pytest.mark.asyncio
async def test_get_context():
    with patch("main.run_ssh_command", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = ["board info", "memory info", "uptime info", "cpu info"]
        res = await main.get_context()
        assert "board info" in res
        assert "memory info" in res
        assert "uptime info" in res
        assert "cpu info" in res
        mock_run.assert_any_call("ubus call system board")
        mock_run.assert_any_call("free -h")
        mock_run.assert_any_call("uptime")
        mock_run.assert_any_call(
            "grep -E 'model name|system type|machine' /proc/cpuinfo | uniq"
        )


@pytest.mark.asyncio
async def test_get_routing_table():
    with patch("main.run_ssh_command", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = ["ipv4 route show", "ipv6 route show"]
        res = await main.get_routing_table()
        assert "ipv4 route show" in res
        assert "ipv6 route show" in res
        mock_run.assert_any_call("ip route show")
        mock_run.assert_any_call("ip -6 route show")


@pytest.mark.asyncio
async def test_get_firewall_rules():
    with patch("main.run_ssh_command", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = "firewall rules"
        res = await main.get_firewall_rules()
        assert res == "firewall rules"
        mock_run.assert_called_once_with("uci show firewall")


@pytest.mark.asyncio
async def test_check_internet_connection():
    with patch("main.run_ssh_command", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = ["ping output", "nslookup output", "wget output"]
        res = await main.check_internet_connection()
        assert "ping output" in res
        assert "nslookup output" in res
        assert "wget output" in res
        mock_run.assert_any_call("ping -c 2 8.8.8.8")
        mock_run.assert_any_call("nslookup google.com")
        mock_run.assert_any_call("wget -q -O- http://neverssl.com | head -n 5")
