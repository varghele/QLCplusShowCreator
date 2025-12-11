# gui/tabs/stage_tab.py

from PyQt6 import QtWidgets
from config.models import Configuration
from .base_tab import BaseTab
from gui.StageView import StageView


class StageTab(BaseTab):
    """Stage layout and fixture positioning tab

    Provides visual stage representation with fixture positioning,
    grid controls, and spot/mark management. Composes the existing
    StageView component with control panel UI.
    """

    def __init__(self, config: Configuration, parent=None):
        """Initialize stage tab

        Args:
            config: Shared Configuration object
            parent: Parent widget (typically MainWindow)
        """
        super().__init__(config, parent)

    def setup_ui(self):
        """Set up stage visualization UI"""
        # Create main layout for the tab
        main_layout = QtWidgets.QHBoxLayout(self)

        # Left control panel
        control_panel = QtWidgets.QWidget()
        control_layout = QtWidgets.QVBoxLayout(control_panel)
        control_panel.setFixedWidth(250)

        # Stage dimensions group
        dim_group = QtWidgets.QGroupBox("Stage Dimensions")
        dim_layout = QtWidgets.QFormLayout(dim_group)

        self.stage_width = QtWidgets.QSpinBox()
        self.stage_width.setRange(1, 1000)
        self.stage_width.setValue(10)  # Default 10 meters

        self.stage_height = QtWidgets.QSpinBox()
        self.stage_height.setRange(1, 1000)
        self.stage_height.setValue(6)  # Default 6 meters

        dim_layout.addRow("Width (m):", self.stage_width)
        dim_layout.addRow("Depth (m):", self.stage_height)

        # Update and save stage buttons
        self.update_stage_btn = QtWidgets.QPushButton("Update Stage")
        dim_layout.addRow(self.update_stage_btn)

        self.save_stage_btn = QtWidgets.QPushButton("Save Stage")
        dim_layout.addRow(self.save_stage_btn)

        # Grid controls group
        grid_group = QtWidgets.QGroupBox("Grid Settings")
        grid_layout = QtWidgets.QFormLayout(grid_group)

        self.grid_toggle = QtWidgets.QCheckBox("Show Grid")
        self.grid_toggle.setChecked(True)  # Grid visible by default

        self.grid_size = QtWidgets.QDoubleSpinBox()
        self.grid_size.setRange(0.1, 50)
        self.grid_size.setValue(0.5)  # Default 0.5m grid
        self.grid_size.setSingleStep(0.1)

        self.snap_to_grid = QtWidgets.QCheckBox("Snap to Grid")

        grid_layout.addRow(self.grid_toggle)
        grid_layout.addRow("Grid Size (m):", self.grid_size)
        grid_layout.addRow(self.snap_to_grid)

        # Stage marks group
        spot_group = QtWidgets.QGroupBox("Stage Marks")
        spot_layout = QtWidgets.QVBoxLayout(spot_group)

        self.add_spot_btn = QtWidgets.QPushButton("Add Mark")
        self.remove_item_btn = QtWidgets.QPushButton("Remove Selected")

        spot_layout.addWidget(self.add_spot_btn)
        spot_layout.addWidget(self.remove_item_btn)

        # Plot stage group
        plot_group = QtWidgets.QGroupBox("Stage Plot")
        plot_layout = QtWidgets.QVBoxLayout(plot_group)

        self.plot_stage_btn = QtWidgets.QPushButton("Plot Stage")
        plot_layout.addWidget(self.plot_stage_btn)

        # Add groups to control panel in order
        control_layout.addWidget(dim_group)
        control_layout.addWidget(grid_group)
        control_layout.addWidget(spot_group)
        control_layout.addWidget(plot_group)
        control_layout.addStretch()

        # Create stage view area (right side)
        stage_view_container = QtWidgets.QWidget()
        stage_view_layout = QtWidgets.QVBoxLayout(stage_view_container)

        # Initialize StageView with configuration
        self.stage_view = StageView(self)
        self.stage_view.set_config(self.config)
        stage_view_layout.addWidget(self.stage_view)

        # Add both panels to main layout
        main_layout.addWidget(control_panel)
        main_layout.addWidget(stage_view_container, stretch=1)

    def connect_signals(self):
        """Connect widget signals to handlers"""
        # Stage dimension controls
        self.update_stage_btn.clicked.connect(self._update_stage)
        self.save_stage_btn.clicked.connect(self.save_to_config)

        # Grid controls
        self.grid_toggle.stateChanged.connect(
            lambda state: self.stage_view.updateGrid(visible=bool(state))
        )
        self.grid_size.valueChanged.connect(
            lambda value: self.stage_view.updateGrid(size_m=value)
        )
        self.snap_to_grid.stateChanged.connect(
            lambda state: self.stage_view.set_snap_to_grid(bool(state))
        )

        # Spot/mark controls
        self.add_spot_btn.clicked.connect(lambda: self.stage_view.add_spot())
        self.remove_item_btn.clicked.connect(self.stage_view.remove_selected_items)

    def update_from_config(self):
        """Refresh stage view from configuration"""
        if self.stage_view:
            self.stage_view.set_config(self.config)

    def save_to_config(self):
        """Save fixture positions and spots back to configuration"""
        if self.stage_view:
            self.stage_view.save_positions_to_config()

    def _update_stage(self):
        """Update stage dimensions from spin box values"""
        self.stage_view.updateStage(
            self.stage_width.value(),
            self.stage_height.value()
        )
        self.stage_view.update_from_config()
