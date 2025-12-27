# utils/tcp/protocol.py
# Protocol definition for Show Creator <-> Visualizer communication

import json
from enum import Enum
from typing import Dict, List, Any
from config.models import Configuration, Fixture, FixtureGroup


class MessageType(Enum):
    """Message types for Visualizer protocol."""
    STAGE = "stage"
    FIXTURES = "fixtures"
    GROUPS = "groups"
    UPDATE = "update"
    HEARTBEAT = "heartbeat"
    ACK = "ack"


class VisualizerProtocol:
    """
    Protocol for sending configuration data to Visualizer via TCP.

    Messages are JSON-formatted with a newline delimiter.
    """

    @staticmethod
    def create_stage_message(config: Configuration) -> str:
        """
        Create stage dimensions message.

        Args:
            config: Configuration with stage settings

        Returns:
            JSON string with newline delimiter
        """
        message = {
            "type": MessageType.STAGE.value,
            "width": config.stage_width,
            "height": config.stage_height
        }
        return json.dumps(message) + "\n"

    @staticmethod
    def create_fixtures_message(config: Configuration) -> str:
        """
        Create fixtures list message.

        Args:
            config: Configuration with fixtures

        Returns:
            JSON string with newline delimiter
        """
        fixtures_data = []

        for fixture in config.fixtures:
            fixture_info = {
                "name": fixture.name,
                "manufacturer": fixture.manufacturer,
                "model": fixture.model,
                "mode": fixture.current_mode,
                "universe": fixture.universe,
                "address": fixture.address,
                "position": {
                    "x": fixture.x,
                    "y": fixture.y,
                    "z": fixture.z
                }
            }
            fixtures_data.append(fixture_info)

        message = {
            "type": MessageType.FIXTURES.value,
            "fixtures": fixtures_data
        }
        return json.dumps(message) + "\n"

    @staticmethod
    def create_groups_message(config: Configuration) -> str:
        """
        Create groups message.

        Args:
            config: Configuration with groups

        Returns:
            JSON string with newline delimiter
        """
        groups_data = []

        for group_name, group in config.groups.items():
            group_info = {
                "name": group_name,
                "color": group.color,
                "fixtures": [fixture.name for fixture in group.fixtures]
            }
            groups_data.append(group_info)

        message = {
            "type": MessageType.GROUPS.value,
            "groups": groups_data
        }
        return json.dumps(message) + "\n"

    @staticmethod
    def create_update_message(update_type: str, data: Dict[str, Any]) -> str:
        """
        Create update notification message.

        Args:
            update_type: Type of update (e.g., "fixture_moved", "config_changed")
            data: Update-specific data

        Returns:
            JSON string with newline delimiter
        """
        message = {
            "type": MessageType.UPDATE.value,
            "update_type": update_type,
            "data": data
        }
        return json.dumps(message) + "\n"

    @staticmethod
    def create_heartbeat_message() -> str:
        """
        Create heartbeat message to keep connection alive.

        Returns:
            JSON string with newline delimiter
        """
        message = {
            "type": MessageType.HEARTBEAT.value,
            "timestamp": None  # Will be filled by server
        }
        return json.dumps(message) + "\n"

    @staticmethod
    def create_ack_message(original_type: str) -> str:
        """
        Create acknowledgment message.

        Args:
            original_type: Type of message being acknowledged

        Returns:
            JSON string with newline delimiter
        """
        message = {
            "type": MessageType.ACK.value,
            "ack_type": original_type
        }
        return json.dumps(message) + "\n"

    @staticmethod
    def parse_message(data: str) -> Dict[str, Any]:
        """
        Parse incoming JSON message.

        Args:
            data: JSON string (with or without newline)

        Returns:
            Parsed message dictionary
        """
        return json.loads(data.strip())

    @staticmethod
    def serialize_full_config(config: Configuration) -> List[str]:
        """
        Serialize complete configuration as a sequence of messages.

        Args:
            config: Configuration to serialize

        Returns:
            List of JSON message strings
        """
        messages = []

        # Send stage dimensions first
        messages.append(VisualizerProtocol.create_stage_message(config))

        # Send fixtures
        messages.append(VisualizerProtocol.create_fixtures_message(config))

        # Send groups
        messages.append(VisualizerProtocol.create_groups_message(config))

        return messages
