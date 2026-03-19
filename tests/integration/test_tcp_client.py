# tests/integration/test_tcp_client.py
"""Integration test for TCP Visualizer protocol client.

Requires a running Visualizer server on localhost:9000.

Run with: pytest tests/integration/test_tcp_client.py -v -m integration
"""

import socket
import json
import pytest

pytestmark = pytest.mark.integration


class TestTcpVisualizerClient:
    """Tests for TCP connection to Visualizer server.

    These tests require a running server and are skipped by default.
    """

    @pytest.fixture
    def server_available(self):
        """Check if the Visualizer server is running."""
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.settimeout(1.0)
        try:
            test_socket.connect(("localhost", 9000))
            test_socket.close()
            return True
        except (ConnectionRefusedError, OSError):
            pytest.skip("Visualizer server not running on localhost:9000")

    def test_connect_and_receive_config(self, server_available):
        """Test connecting to server and receiving initial configuration."""
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5.0)

        try:
            client.connect(("localhost", 9000))
            buffer = ""
            messages = []

            # Receive up to 3 config messages (stage, fixtures, groups)
            while len(messages) < 3:
                data = client.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')

                while '\n' in buffer:
                    msg_str, buffer = buffer.split('\n', 1)
                    if msg_str.strip():
                        msg = json.loads(msg_str)
                        messages.append(msg)

            # Verify we got the expected message types
            types = {m.get('type') for m in messages}
            assert "stage" in types
            assert "fixtures" in types
            assert "groups" in types

        finally:
            client.close()

    def test_stage_message_format(self, server_available):
        """Test that stage message contains required fields."""
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5.0)

        try:
            client.connect(("localhost", 9000))
            buffer = ""

            data = client.recv(4096)
            buffer = data.decode('utf-8')

            if '\n' in buffer:
                msg_str = buffer.split('\n')[0]
                msg = json.loads(msg_str)

                if msg.get('type') == 'stage':
                    assert 'width' in msg
                    assert 'height' in msg
                    assert isinstance(msg['width'], (int, float))
                    assert isinstance(msg['height'], (int, float))

        finally:
            client.close()