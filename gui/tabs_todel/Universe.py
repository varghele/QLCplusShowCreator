from PyQt6 import QtWidgets


class UniverseDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Universe")
        layout = QtWidgets.QFormLayout(self)

        # Universe number
        self.universe_num = QtWidgets.QSpinBox()
        self.universe_num.setRange(1, 16)
        layout.addRow("Universe Number:", self.universe_num)

        # Output type
        self.output_type = QtWidgets.QComboBox()
        self.output_type.addItems(["E1.31", "ArtNet", "DMX"])
        layout.addRow("Output Type:", self.output_type)

        # IP Address
        self.ip_address = QtWidgets.QLineEdit()
        self.ip_address.setPlaceholderText("192.168.1.255")
        layout.addRow("IP Address:", self.ip_address)

        # Port
        self.port = QtWidgets.QLineEdit()
        self.port.setPlaceholderText("6454")
        layout.addRow("Port:", self.port)

        # Subnet
        self.subnet = QtWidgets.QLineEdit()
        self.subnet.setPlaceholderText("0")
        layout.addRow("Subnet:", self.subnet)

        # Universe
        self.universe = QtWidgets.QLineEdit()
        self.universe.setPlaceholderText("1")
        layout.addRow("Universe:", self.universe)

        # Buttons
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
