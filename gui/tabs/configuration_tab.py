# gui/tabs/configuration_tab.py

from PyQt6 import QtWidgets, QtCore
from PyQt6.QtGui import QFont
from config.models import Configuration
from .base_tab import BaseTab


class ConfigurationTab(BaseTab):
    """Universe configuration management tab

    Handles DMX universe configuration including E1.31, ArtNet, and DMX USB settings.
    Provides table-based interface for adding, removing, and editing universe parameters.
    """

    def __init__(self, config: Configuration, parent=None):
        """Initialize configuration tab

        Args:
            config: Shared Configuration object
            parent: Parent widget (typically MainWindow)
        """
        # Initialize universes before setup_ui is called
        if not hasattr(config, 'universes'):
            config.universes = {}
            config.initialize_default_universes()

        super().__init__(config, parent)

    def setup_ui(self):
        """Set up universe configuration UI"""
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Button toolbar
        toolbar = QtWidgets.QHBoxLayout()
        toolbar.setSpacing(8)

        # Add Universe button
        self.add_universe_btn = QtWidgets.QPushButton("+")
        self.add_universe_btn.setFixedSize(31, 31)
        self.add_universe_btn.setToolTip("Add Universe")
        toolbar.addWidget(self.add_universe_btn)

        # Remove Universe button
        self.remove_universe_btn = QtWidgets.QPushButton("-")
        self.remove_universe_btn.setFixedSize(31, 31)
        self.remove_universe_btn.setToolTip("Remove Universe")
        toolbar.addWidget(self.remove_universe_btn)

        # Update Config button
        self.update_config_btn = QtWidgets.QPushButton("Update Config")
        self.update_config_btn.setFixedWidth(115)
        self.update_config_btn.setToolTip("Update Configuration")
        toolbar.addWidget(self.update_config_btn)

        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # Config label
        self.config_label = QtWidgets.QLabel("Config")
        self.config_label.setFont(QFont("", 14, QFont.Weight.Bold))
        main_layout.addWidget(self.config_label)

        # Universe list table
        self.universe_list = QtWidgets.QTableWidget()
        self.universe_list.setColumnCount(6)
        self.universe_list.setHorizontalHeaderLabels([
            "Universe", "Output Type", "IP Address", "Port", "Subnet", "Universe"
        ])

        # Set table properties
        self.universe_list.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.universe_list.setSelectionMode(
            QtWidgets.QAbstractItemView.SelectionMode.SingleSelection
        )

        # Make table stretch to fill available space
        self.universe_list.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Expanding,
            QtWidgets.QSizePolicy.Policy.Expanding
        )
        self.universe_list.horizontalHeader().setStretchLastSection(True)
        self.universe_list.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Interactive
        )

        # Set initial column widths (these are now resizable)
        self.universe_list.setColumnWidth(0, 80)   # Universe
        self.universe_list.setColumnWidth(1, 120)  # Output Type
        self.universe_list.setColumnWidth(2, 150)  # IP Address
        self.universe_list.setColumnWidth(3, 80)   # Port
        self.universe_list.setColumnWidth(4, 80)   # Subnet
        self.universe_list.setColumnWidth(5, 80)   # Universe

        main_layout.addWidget(self.universe_list)

        # Load initial data
        self.update_from_config()

    def connect_signals(self):
        """Connect widget signals to handlers"""
        self.add_universe_btn.clicked.connect(self._add_universe)
        self.remove_universe_btn.clicked.connect(self._remove_universe)
        self.update_config_btn.clicked.connect(self.save_to_config)
        self.universe_list.itemChanged.connect(self._on_universe_item_changed)

    def update_from_config(self):
        """Load universes from configuration to table"""
        # Block signals to prevent triggering itemChanged during population
        self.universe_list.blockSignals(True)

        # Clear the table first
        self.universe_list.setRowCount(0)

        if hasattr(self.config, 'universes'):
            for universe_id, universe in self.config.universes.items():
                row = self.universe_list.rowCount()
                self.universe_list.insertRow(row)

                # Universe ID
                self.universe_list.setItem(
                    row, 0, QtWidgets.QTableWidgetItem(str(universe.id))
                )

                # Output type combo
                output_combo = QtWidgets.QComboBox()
                output_combo.addItems(["E1.31", "ArtNet", "DMX"])
                output_combo.setCurrentText(universe.output.get('plugin', 'E1.31'))
                output_combo.currentTextChanged.connect(
                    lambda text, r=row: self._on_output_type_changed(r)
                )
                self.universe_list.setCellWidget(row, 1, output_combo)

                # Parameters
                params = universe.output.get('parameters', {})
                self.universe_list.setItem(
                    row, 2, QtWidgets.QTableWidgetItem(params.get('ip', ''))
                )
                self.universe_list.setItem(
                    row, 3, QtWidgets.QTableWidgetItem(params.get('port', ''))
                )
                self.universe_list.setItem(
                    row, 4, QtWidgets.QTableWidgetItem(params.get('subnet', ''))
                )
                self.universe_list.setItem(
                    row, 5, QtWidgets.QTableWidgetItem(params.get('universe', ''))
                )

        # Re-enable signals
        self.universe_list.blockSignals(False)

    def save_to_config(self):
        """Update universe configuration from table values"""
        for row in range(self.universe_list.rowCount()):
            # Check if we have a valid universe ID in the first column
            universe_id_item = self.universe_list.item(row, 0)
            if universe_id_item is None or not universe_id_item.text():
                continue

            try:
                universe_id = int(universe_id_item.text())

                # Skip if this universe doesn't exist in config
                if universe_id not in self.config.universes:
                    continue

                # Update IP Address
                ip_item = self.universe_list.item(row, 2)
                if ip_item and ip_item.text():
                    self.config.universes[universe_id].output['parameters']['ip'] = ip_item.text()

                # Update Port
                port_item = self.universe_list.item(row, 3)
                if port_item and port_item.text():
                    self.config.universes[universe_id].output['parameters']['port'] = port_item.text()

                # Update Subnet
                subnet_item = self.universe_list.item(row, 4)
                if subnet_item and subnet_item.text():
                    self.config.universes[universe_id].output['parameters']['subnet'] = subnet_item.text()

                # Update Universe
                uni_item = self.universe_list.item(row, 5)
                if uni_item and uni_item.text():
                    self.config.universes[universe_id].output['parameters']['universe'] = uni_item.text()

            except (ValueError, AttributeError) as e:
                print(f"Error updating universe {row}: {e}")

        print("Universe configuration updated from table")

    def _add_universe(self):
        """Add a new universe configuration"""
        row = self.universe_list.rowCount()
        universe_id = row + 1

        # Add new universe to configuration
        self.config.add_universe(
            universe_id=universe_id,
            output_type='E1.31',
            ip=f'192.168.1.{universe_id}',
            port='6454',
            subnet='0',
            universe=str(universe_id)
        )

        # Update table
        self.update_from_config()

    def _remove_universe(self):
        """Remove selected universe configuration"""
        current_row = self.universe_list.currentRow()
        if current_row >= 0:
            universe_id_item = self.universe_list.item(current_row, 0)
            if universe_id_item:
                universe_id = int(universe_id_item.text())
                if universe_id in self.config.universes:
                    self.config.remove_universe(universe_id)
                self.universe_list.removeRow(current_row)

    def _on_universe_item_changed(self, item):
        """Handle changes to universe table items"""
        row = item.row()
        col = item.column()
        universe_id_item = self.universe_list.item(row, 0)

        if universe_id_item:
            universe_id = int(universe_id_item.text())

            if universe_id in self.config.universes:
                # Update the appropriate field based on the column
                if col == 2:  # IP Address
                    self.config.universes[universe_id].output['parameters']['ip'] = item.text()
                elif col == 3:  # Port
                    self.config.universes[universe_id].output['parameters']['port'] = item.text()
                elif col == 4:  # Subnet
                    self.config.universes[universe_id].output['parameters']['subnet'] = item.text()
                elif col == 5:  # Universe
                    self.config.universes[universe_id].output['parameters']['universe'] = item.text()

    def _on_output_type_changed(self, row):
        """Handle output type changes"""
        output_combo = self.universe_list.cellWidget(row, 1)
        universe_id_item = self.universe_list.item(row, 0)

        if output_combo and universe_id_item:
            output_type = output_combo.currentText()
            universe_id = int(universe_id_item.text())

            if universe_id in self.config.universes:
                self.config.universes[universe_id].output['plugin'] = output_type
