# timeline_ui/effect_block_dialog.py
# Dialog for editing light effect block parameters

import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QGroupBox, QComboBox, QPushButton, QSlider,
                             QSpinBox, QLabel, QDialogButtonBox, QTreeWidget,
                             QTreeWidgetItem, QLineEdit)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from config.models import LightBlock


class EffectBlockDialog(QDialog):
    """Dialog for selecting effect and setting parameters for a light block."""

    def __init__(self, block: LightBlock, parent=None):
        """Create the effect block dialog.

        Args:
            block: LightBlock to edit
            parent: Parent widget
        """
        super().__init__(parent)
        self.block = block
        self.effects_dir = "effects"
        self.effects_dict = {}

        self.setWindowTitle("Edit Effect Block")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        self.setup_ui()
        self.load_effects()
        self.load_current_values()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Effect selection group
        effect_group = QGroupBox("Effect")
        effect_layout = QVBoxLayout()

        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filter effects...")
        self.search_edit.textChanged.connect(self.filter_effects)
        search_layout.addWidget(self.search_edit)
        effect_layout.addLayout(search_layout)

        # Effect tree
        self.effect_tree = QTreeWidget()
        self.effect_tree.setHeaderHidden(True)
        self.effect_tree.itemDoubleClicked.connect(self.on_effect_double_clicked)
        effect_layout.addWidget(self.effect_tree)

        # Clear effect button
        clear_btn = QPushButton("Clear Effect")
        clear_btn.clicked.connect(self.clear_effect)
        clear_btn.setStyleSheet("background-color: #d32f2f; color: white;")
        effect_layout.addWidget(clear_btn)

        effect_group.setLayout(effect_layout)
        layout.addWidget(effect_group)

        # Parameters group
        params_group = QGroupBox("Parameters")
        params_layout = QFormLayout()

        # Speed
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(['1/32', '1/16', '1/8', '1/4', '1/2', '1', '2', '4', '8', '16', '32'])
        self.speed_combo.setCurrentText('1')
        params_layout.addRow("Speed:", self.speed_combo)

        # Color
        color_layout = QHBoxLayout()
        self.color_btn = QPushButton()
        self.color_btn.setFixedHeight(30)
        self.color_btn.clicked.connect(self.select_color)
        self.color_btn.setStyleSheet("background-color: #808080;")
        self.color_label = QLabel("#808080")
        color_layout.addWidget(self.color_btn, 1)
        color_layout.addWidget(self.color_label)
        params_layout.addRow("Color:", color_layout)

        # Intensity
        intensity_layout = QHBoxLayout()
        self.intensity_slider = QSlider(Qt.Orientation.Horizontal)
        self.intensity_slider.setRange(0, 255)
        self.intensity_slider.setValue(200)
        self.intensity_spinbox = QSpinBox()
        self.intensity_spinbox.setRange(0, 255)
        self.intensity_spinbox.setValue(200)
        self.intensity_slider.valueChanged.connect(self.intensity_spinbox.setValue)
        self.intensity_spinbox.valueChanged.connect(self.intensity_slider.setValue)
        intensity_layout.addWidget(self.intensity_slider, 1)
        intensity_layout.addWidget(self.intensity_spinbox)
        params_layout.addRow("Intensity:", intensity_layout)

        # Spot (optional)
        self.spot_combo = QComboBox()
        self.spot_combo.addItem("")  # Empty option
        # TODO: Populate with spots from configuration
        params_layout.addRow("Spot:", self.spot_combo)

        params_group.setLayout(params_layout)
        layout.addWidget(params_group)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_effects(self):
        """Load available effects from effects directory."""
        self.effects_dict = {}
        self.effect_tree.clear()

        try:
            # Check if effects.json exists
            effects_json_path = os.path.join(self.effects_dir, "effects.json")
            if os.path.exists(effects_json_path):
                import json
                with open(effects_json_path, 'r') as f:
                    self.effects_dict = json.load(f)
            else:
                # Scan for .py files and use AST to find functions
                self._scan_effect_files()

            # Populate tree
            for module_name, effects in sorted(self.effects_dict.items()):
                module_item = QTreeWidgetItem(self.effect_tree, [module_name])
                module_item.setExpanded(True)

                for effect_name in sorted(effects):
                    effect_item = QTreeWidgetItem(module_item, [effect_name])
                    effect_item.setData(0, Qt.ItemDataRole.UserRole, f"{module_name}.{effect_name}")

        except Exception as e:
            print(f"Error loading effects: {e}")

    def _scan_effect_files(self):
        """Scan effect files using AST to find functions."""
        import ast

        if not os.path.exists(self.effects_dir):
            return

        for filename in os.listdir(self.effects_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]
                filepath = os.path.join(self.effects_dir, filename)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        tree = ast.parse(f.read())

                    functions = []
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            # Skip private functions
                            if not node.name.startswith('_'):
                                functions.append(node.name)

                    if functions:
                        self.effects_dict[module_name] = functions

                except Exception as e:
                    print(f"Error parsing {filepath}: {e}")

    def filter_effects(self, text):
        """Filter effects tree based on search text."""
        text = text.lower()

        for i in range(self.effect_tree.topLevelItemCount()):
            module_item = self.effect_tree.topLevelItem(i)
            module_visible = False

            for j in range(module_item.childCount()):
                effect_item = module_item.child(j)
                effect_name = effect_item.text(0).lower()
                visible = text in effect_name or text in module_item.text(0).lower()
                effect_item.setHidden(not visible)
                if visible:
                    module_visible = True

            module_item.setHidden(not module_visible)
            if module_visible:
                module_item.setExpanded(True)

    def load_current_values(self):
        """Load current block values into the dialog."""
        # Effect selection
        if self.block.effect_name:
            self._select_effect_in_tree(self.block.effect_name)

        # Parameters
        params = self.block.parameters

        if params.get('speed'):
            self.speed_combo.setCurrentText(str(params['speed']))

        if params.get('color'):
            color = params['color']
            self.color_btn.setStyleSheet(f"background-color: {color};")
            self.color_label.setText(color)

        if params.get('intensity') is not None:
            self.intensity_slider.setValue(int(params['intensity']))

        if params.get('spot'):
            idx = self.spot_combo.findText(params['spot'])
            if idx >= 0:
                self.spot_combo.setCurrentIndex(idx)

    def _select_effect_in_tree(self, effect_name: str):
        """Select an effect in the tree by its full name."""
        for i in range(self.effect_tree.topLevelItemCount()):
            module_item = self.effect_tree.topLevelItem(i)
            for j in range(module_item.childCount()):
                effect_item = module_item.child(j)
                if effect_item.data(0, Qt.ItemDataRole.UserRole) == effect_name:
                    self.effect_tree.setCurrentItem(effect_item)
                    return

    def select_color(self):
        """Open color picker dialog."""
        from PyQt6.QtWidgets import QColorDialog

        current_color = QColor(self.color_label.text())
        color = QColorDialog.getColor(
            initial=current_color,
            options=QColorDialog.ColorDialogOption.ShowAlphaChannel
        )

        if color.isValid():
            hex_color = color.name().upper()
            self.color_btn.setStyleSheet(f"background-color: {hex_color};")
            self.color_label.setText(hex_color)

    def clear_effect(self):
        """Clear the selected effect."""
        self.effect_tree.clearSelection()
        self.block.effect_name = ""

    def on_effect_double_clicked(self, item, column):
        """Handle double-click on effect to select and close."""
        if item.parent():  # It's an effect, not a module
            self.accept()

    def get_selected_effect(self) -> str:
        """Get the currently selected effect name."""
        selected = self.effect_tree.currentItem()
        if selected and selected.parent():  # Has parent = effect item
            return selected.data(0, Qt.ItemDataRole.UserRole)
        return ""

    def accept(self):
        """Save parameters to block and close."""
        # Save effect name
        self.block.effect_name = self.get_selected_effect()

        # Save parameters
        self.block.parameters = {
            'speed': self.speed_combo.currentText(),
            'color': self.color_label.text(),
            'intensity': self.intensity_spinbox.value(),
            'spot': self.spot_combo.currentText()
        }

        super().accept()
