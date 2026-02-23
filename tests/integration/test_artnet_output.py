# tests/integration/test_artnet_output.py
"""Integration test for ArtNet DMX output.

Requires:
- QApplication (PyQt6)
- config.yaml in project root
- ArtNet controller module

Run with: pytest tests/integration/test_artnet_output.py -v -m integration
"""

import os
import sys
import time
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def qapp():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def config():
    from config.models import Configuration
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config.yaml")
    if not os.path.exists(config_path):
        pytest.skip("config.yaml not found in project root")
    return Configuration.load(config_path)


@pytest.fixture
def playback_engine(qapp):
    from timeline.playback_engine import PlaybackEngine
    return PlaybackEngine()


class TestArtNetOutput:
    """Integration tests for ArtNet output controller."""

    def test_controller_creation(self, qapp, config, playback_engine):
        """Test that ArtNet controller can be created with real config."""
        from utils.artnet import ArtNetOutputController

        controller = ArtNetOutputController(
            config=config,
            fixture_definitions={},
            playback_engine=playback_engine,
            target_ip="127.0.0.1",
        )
        assert controller is not None

    def test_enable_disable_output(self, qapp, config, playback_engine):
        """Test enabling and disabling ArtNet output."""
        from utils.artnet import ArtNetOutputController

        controller = ArtNetOutputController(
            config=config,
            fixture_definitions={},
            playback_engine=playback_engine,
            target_ip="127.0.0.1",
        )
        controller.enable_output()
        controller.cleanup()

    def test_dmx_manager_block_started(self, qapp, config, playback_engine):
        """Test sending a dimmer block through DMX manager."""
        from utils.artnet import ArtNetOutputController
        from config.models import DimmerBlock

        controller = ArtNetOutputController(
            config=config,
            fixture_definitions={},
            playback_engine=playback_engine,
            target_ip="127.0.0.1",
        )

        for group_name, group in config.groups.items():
            dimmer_block = DimmerBlock(
                start_time=0.0, end_time=10.0,
                intensity=128, effect_type="static",
            )
            controller.dmx_manager.block_started(
                group_name, list(group.fixtures), dimmer_block, 'dimmer', 0.0,
            )
            break  # Only test first group

        controller.cleanup()