# tests/unit/test_artnet_sender.py
"""Unit tests for utils/artnet/sender.py - ArtNet packet creation."""

import struct
import pytest
from unittest.mock import patch, MagicMock
from utils.artnet.sender import ArtNetSender


@pytest.fixture
def sender():
    """Create an ArtNetSender with mocked socket."""
    with patch('utils.artnet.sender.socket.socket') as mock_sock:
        s = ArtNetSender(target_ip="127.0.0.1")
        s.socket = MagicMock()
        yield s


class TestCreateDmxPacket:

    def test_packet_length(self, sender):
        packet = sender.create_dmx_packet(0, bytes(512))
        # 8 (header) + 2 (opcode) + 2 (version) + 1 (seq) + 1 (physical)
        # + 2 (universe) + 2 (length) + 512 (data) = 530
        assert len(packet) == 530

    def test_header(self, sender):
        packet = sender.create_dmx_packet(0, bytes(10))
        assert packet[:8] == b'Art-Net\x00'

    def test_opcode(self, sender):
        packet = sender.create_dmx_packet(0, bytes(10))
        opcode = struct.unpack('<H', packet[8:10])[0]
        assert opcode == 0x5000

    def test_protocol_version(self, sender):
        packet = sender.create_dmx_packet(0, bytes(10))
        version = struct.unpack('>H', packet[10:12])[0]
        assert version == 0x000e  # Version 14

    def test_universe_encoding(self, sender):
        packet = sender.create_dmx_packet(5, bytes(10))
        universe = struct.unpack('<H', packet[14:16])[0]
        assert universe == 5

    def test_data_length(self, sender):
        packet = sender.create_dmx_packet(0, bytes(100))
        length = struct.unpack('>H', packet[16:18])[0]
        assert length == 512  # Padded to 512

    def test_short_data_padded(self, sender):
        data = bytes([255, 128, 64])
        packet = sender.create_dmx_packet(0, data)
        # Data starts at byte 18
        assert packet[18] == 255
        assert packet[19] == 128
        assert packet[20] == 64
        assert packet[21] == 0  # Padded

    def test_long_data_truncated(self, sender):
        data = bytes([200] * 600)
        packet = sender.create_dmx_packet(0, data)
        assert len(packet) == 530  # Still 530 total

    def test_sequence_counter_increments(self, sender):
        sender.sequence = 0
        packet1 = sender.create_dmx_packet(0, bytes(10))
        assert packet1[12] == 0
        packet2 = sender.create_dmx_packet(0, bytes(10))
        assert packet2[12] == 1

    def test_sequence_wraps_at_256(self, sender):
        sender.sequence = 255
        packet = sender.create_dmx_packet(0, bytes(10))
        assert packet[12] == 255
        assert sender.sequence == 0  # Wrapped

    def test_physical_port_is_zero(self, sender):
        packet = sender.create_dmx_packet(0, bytes(10))
        assert packet[13] == 0


class TestSendDmx:

    def test_send_success(self, sender):
        sender.socket.sendto = MagicMock()
        result = sender.send_dmx(0, bytes(10), force=True)
        assert result is True
        sender.socket.sendto.assert_called_once()

    def test_rate_limiting(self, sender):
        sender.socket.sendto = MagicMock()
        # First send should work
        result1 = sender.send_dmx(0, bytes(10), force=True)
        assert result1 is True
        # Immediate second send should be rate-limited (not forced)
        result2 = sender.send_dmx(0, bytes(10), force=False)
        assert result2 is False

    def test_force_bypasses_rate_limit(self, sender):
        sender.socket.sendto = MagicMock()
        sender.send_dmx(0, bytes(10), force=True)
        result = sender.send_dmx(0, bytes(10), force=True)
        assert result is True

    def test_different_universes_independent(self, sender):
        sender.socket.sendto = MagicMock()
        sender.send_dmx(0, bytes(10), force=True)
        # Different universe should not be rate-limited
        result = sender.send_dmx(1, bytes(10), force=False)
        assert result is True

    def test_socket_error_returns_false(self, sender):
        sender.socket.sendto = MagicMock(side_effect=OSError("Network error"))
        result = sender.send_dmx(0, bytes(10), force=True)
        assert result is False


class TestSenderInit:

    def test_default_port(self):
        assert ArtNetSender.ARTNET_PORT == 6454

    def test_max_rate(self):
        assert ArtNetSender.MAX_SEND_RATE_HZ == 44

    def test_min_interval(self):
        expected = 1.0 / 44
        assert abs(ArtNetSender.MIN_SEND_INTERVAL - expected) < 0.001