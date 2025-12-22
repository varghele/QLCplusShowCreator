# test_sublane_blocks.py
# Test sublane block rendering within effect envelopes

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt

from config.models import (
    Configuration, Fixture, FixtureMode, FixtureGroup,
    DimmerBlock, ColourBlock, MovementBlock, SpecialBlock
)
from timeline.light_lane import LightLane
from timeline_ui.light_lane_widget import LightLaneWidget


class SublaneBlockTestWindow(QMainWindow):
    """Test window to visualize sublane block rendering."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sublane Block Rendering Test")
        self.setGeometry(100, 100, 1400, 600)

        # Create test configuration
        self.config = self.create_test_config()

        # Setup UI
        self.setup_ui()

    def create_test_config(self):
        """Create a test configuration with a moving head fixture."""
        config = Configuration()

        # Moving Head fixture (4 sublanes)
        moving_head = Fixture(
            universe=1,
            address=1,
            manufacturer="Varytec",
            model="Hero Spot 60",
            name="MH1",
            group="Moving Heads",
            direction="",
            current_mode="14-Channel",
            available_modes=[FixtureMode("14-Channel", 14)],
            type="MH"
        )

        config.groups["Moving Heads"] = FixtureGroup(
            name="Moving Heads",
            fixtures=[moving_head]
        )

        return config

    def setup_ui(self):
        """Setup the test UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)

        # Title
        title = QLabel("Sublane Block Rendering Test")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white; background-color: #333; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Description
        desc = QLabel(
            "This test shows MULTIPLE sublane blocks per type:\n"
            "- Yellow blocks = Dimmer sublane (Block 2 has TWO!)\n"
            "- Green/Color blocks = Colour sublane (Block 4 has THREE!)\n"
            "- Blue blocks = Movement sublane\n"
            "- Purple blocks = Special sublane\n"
            "- Dashed border = Effect envelope\n"
            "- Try dragging in empty areas to create more blocks!"
        )
        desc.setStyleSheet("font-size: 12px; color: #999; padding: 10px;")
        layout.addWidget(desc)

        # Create a light lane with test blocks
        lane = self.create_test_lane()

        # Create the lane widget
        lane_widget = LightLaneWidget(
            lane=lane,
            fixture_groups=list(self.config.groups.keys()),
            parent=self,
            config=self.config
        )

        layout.addWidget(lane_widget)
        layout.addStretch()

    def create_test_lane(self):
        """Create a test lane with sublane blocks."""
        lane = LightLane(
            name="Test Lane",
            fixture_group="Moving Heads"
        )

        # Test Block 1: All sublanes synchronized (0-4 seconds)
        lane.add_light_block_with_sublanes(
            start_time=0.0,
            end_time=4.0,
            effect_name="test.synchronized",
            dimmer_blocks=[DimmerBlock(start_time=0.0, end_time=4.0, intensity=255.0)],
            colour_blocks=[ColourBlock(start_time=0.0, end_time=4.0, red=255.0, green=0.0, blue=0.0)],
            movement_blocks=[MovementBlock(start_time=0.0, end_time=4.0, pan=100.0, tilt=100.0)],
            special_blocks=[SpecialBlock(start_time=0.0, end_time=4.0, gobo_index=1)]
        )

        # Test Block 2: Different sublane timings (5-10 seconds)
        # Also demonstrates MULTIPLE blocks per sublane (2 dimmer blocks)
        lane.add_light_block_with_sublanes(
            start_time=5.0,
            end_time=10.0,
            effect_name="test.varied_timing",
            dimmer_blocks=[
                DimmerBlock(start_time=5.0, end_time=7.0, intensity=200.0),
                DimmerBlock(start_time=7.5, end_time=10.0, intensity=100.0)  # Second dimmer block!
            ],
            colour_blocks=[ColourBlock(start_time=6.0, end_time=9.0, red=0.0, green=255.0, blue=0.0)],
            movement_blocks=[MovementBlock(start_time=5.5, end_time=9.5, pan=200.0, tilt=150.0)],
            special_blocks=[SpecialBlock(start_time=7.0, end_time=8.0, gobo_index=2)]
        )

        # Test Block 3: Only some sublanes active (12-16 seconds)
        lane.add_light_block_with_sublanes(
            start_time=12.0,
            end_time=16.0,
            effect_name="test.partial",
            dimmer_blocks=[DimmerBlock(start_time=12.0, end_time=16.0, intensity=180.0)],
            colour_blocks=[ColourBlock(start_time=12.0, end_time=16.0, red=0.0, green=0.0, blue=255.0)],
            movement_blocks=[],  # No movement
            special_blocks=[]  # No special
        )

        # Test Block 4: Modified effect with asterisk (18-22 seconds)
        # Demonstrates MULTIPLE colour blocks (3 color changes)
        block4 = lane.add_light_block_with_sublanes(
            start_time=18.0,
            end_time=22.0,
            effect_name="test.modified",
            dimmer_blocks=[DimmerBlock(start_time=18.0, end_time=22.0, intensity=255.0)],
            colour_blocks=[
                ColourBlock(start_time=18.0, end_time=19.0, red=255.0, green=0.0, blue=0.0),
                ColourBlock(start_time=19.5, end_time=20.5, red=0.0, green=255.0, blue=0.0),
                ColourBlock(start_time=21.0, end_time=22.0, red=0.0, green=0.0, blue=255.0)
            ],
            movement_blocks=[MovementBlock(start_time=18.0, end_time=22.0, pan=127.5, tilt=127.5)],
            special_blocks=[SpecialBlock(start_time=18.0, end_time=22.0, gobo_index=3)]
        )
        block4.modified = True  # Mark as modified to show asterisk

        return lane


def main():
    """Run the sublane block rendering test."""
    app = QApplication(sys.argv)

    # Set dark theme
    app.setStyleSheet("""
        QMainWindow {
            background-color: #1e1e1e;
        }
        QWidget {
            background-color: #1e1e1e;
            color: white;
        }
    """)

    window = SublaneBlockTestWindow()
    window.show()

    print("=" * 70)
    print("Sublane Block Rendering Test - MULTIPLE BLOCKS PER SUBLANE")
    print("=" * 70)
    print("\nThis test demonstrates MULTIPLE sublane blocks per type:")
    print("1. Block 1 (0-4s): All sublanes synchronized (1 block each)")
    print("2. Block 2 (5-10s): TWO dimmer blocks + different sublane timings")
    print("3. Block 3 (12-16s): Only dimmer and colour sublanes")
    print("4. Block 4 (18-22s): THREE colour blocks (red->green->blue)")
    print("\nLook for:")
    print("- Dashed envelope borders containing sublane blocks")
    print("- MULTIPLE blocks in same sublane row (Block 2 dimmer, Block 4 colour)")
    print("- Colored blocks in correct sublane rows")
    print("- Different block widths based on timing")
    print("- Asterisk (*) on Block 4 name")
    print("\nTry drag-to-create: Drag in empty sublane area to create NEW blocks!")
    print("Close the window to exit.")
    print("=" * 70)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
