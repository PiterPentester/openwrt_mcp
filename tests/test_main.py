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
