from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from config.models import Show, ShowPart, ShowEffect
import os
import csv
from ..effect_selection import EffectSelectionDialog


class ShowTab:
    def __init__(self, main_window):
        self.main_window = main_window
        self.config = main_window.config
        self.tableWidget_3 = main_window.tableWidget_3
        self.comboBox = main_window.comboBox
        self.project_root = main_window.project_root

        # Connect signals
        self.setup_ui_connections()

    def setup_ui_connections(self):
        """Set up signal connections for show tab"""
        self.comboBox.currentTextChanged.connect(self.update_show_tab_from_config)
        self.main_window.pushButton_5.clicked.connect(self.import_show_structure)
        self.main_window.pushButton_6.clicked.connect(self.create_workspace)
        self.main_window.pushButton_7.clicked.connect(self.save_show)

    def import_show_structure(self):
        """Import show structure from CSV files"""
        try:
            # Set up fixed columns
            headers = ['Show Part', 'Fixture Group', 'Effect', 'Speed', 'Color']
            self.tableWidget_3.setColumnCount(len(headers))
            self.tableWidget_3.setHorizontalHeaderLabels(headers)

            # Get all show directories
            shows_dir = os.path.join(self.project_root, "shows")

            # Scan for all show structure files
            for show_dir in os.listdir(shows_dir):
                show_path = os.path.join(shows_dir, show_dir)
                if os.path.isdir(show_path):
                    structure_file = os.path.join(show_path, f"{show_dir}_structure.csv")
                    if os.path.exists(structure_file):
                        # Create new Show object
                        show = Show(name=show_dir)

                        with open(structure_file, 'r') as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                show_part = ShowPart(
                                    name=row['showpart'],
                                    color="#FFFFFF"
                                )
                                show.parts.append(show_part)

                                for group_name in self.config.groups.keys():
                                    effect = ShowEffect(
                                        show_part=show_part.name,
                                        fixture_group=group_name,
                                        effect="",
                                        speed="1",
                                        color=""
                                    )
                                    show.effects.append(effect)

                        self.config.shows[show_dir] = show

            # Update combo box with available shows
            self.comboBox.clear()
            self.comboBox.addItems(sorted(self.config.shows.keys()))

            if self.comboBox.count() > 0:
                self.update_show_tab_from_config()

        except Exception as e:
            print(f"Error importing show structure: {e}")
            import traceback
            traceback.print_exc()

    def create_workspace(self):
        """Create QLC+ workspace from current show configuration"""
        try:
            current_show = self.comboBox.currentText()
            if not current_show or current_show not in self.config.shows:
                QtWidgets.QMessageBox.warning(
                    self.main_window,
                    "Warning",
                    "Please select a show first"
                )
                return

            # Get save location
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self.main_window,
                "Save Workspace",
                os.path.join(self.project_root, "output"),
                "QLC+ Workspace (*.qxw)"
            )

            if not file_path:
                return

            # Create workspace from configuration
            self.config.create_workspace(
                file_path,
                current_show,
                self.project_root
            )

            QtWidgets.QMessageBox.information(
                self.main_window,
                "Success",
                f"Workspace created successfully at:\n{file_path}"
            )

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self.main_window,
                "Error",
                f"Failed to create workspace: {str(e)}"
            )
            import traceback
            traceback.print_exc()

    def update_show_tab_from_config(self):
        """Update show tab when switching to it or when configuration changes"""
        # Clear existing table
        self.tableWidget_3.setRowCount(0)

        # Get current show from combo box
        current_show = self.comboBox.currentText()
        if not current_show or current_show not in self.config.shows:
            return

        show = self.config.shows[current_show]

        # Set up headers if not already done
        headers = ['Show Part', 'Fixture Group', 'Effect', 'Speed', 'Color']
        if self.tableWidget_3.columnCount() != len(headers):
            self.tableWidget_3.setColumnCount(len(headers))
            self.tableWidget_3.setHorizontalHeaderLabels(headers)

        # Add rows for each show part and fixture group combination
        row = 0
        for show_part in show.parts:
            for group_name in sorted(self.config.groups.keys()):
                self.tableWidget_3.insertRow(row)

                # Show Part (read-only)
                show_part_item = QtWidgets.QTableWidgetItem(show_part.name)
                show_part_item.setFlags(show_part_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.tableWidget_3.setItem(row, 0, show_part_item)

                # Fixture Group (read-only)
                group_item = QtWidgets.QTableWidgetItem(group_name)
                group_item.setFlags(group_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.tableWidget_3.setItem(row, 1, group_item)

                # Find existing effect for this combination
                existing_effect = next(
                    (effect for effect in show.effects
                     if effect.show_part == show_part.name
                     and effect.fixture_group == group_name),
                    None
                )

                # Effect button
                effect_button = QtWidgets.QPushButton()
                if existing_effect and existing_effect.effect:
                    effect_button.setText(existing_effect.effect)
                else:
                    effect_button.setText("Select Effect")

                effect_button.clicked.connect(
                    self.create_effect_handler(row, show_part.name, group_name, current_show)
                )
                self.tableWidget_3.setCellWidget(row, 2, effect_button)

                # Speed combo box
                speed_combo = QtWidgets.QComboBox()
                speed_values = ['1/32', '1/16', '1/8', '1/4', '1/2', '1', '2', '4', '8', '16', '32']
                speed_combo.addItems(speed_values)
                if existing_effect:
                    speed_combo.setCurrentText(existing_effect.speed)
                else:
                    speed_combo.setCurrentText('1')

                speed_combo.currentTextChanged.connect(
                    lambda value, r=row: self.update_show_effect(
                        current_show,
                        show_part.name,
                        group_name,
                        self.get_effect(r),
                        value,
                        self.get_color(r)
                    )
                )
                self.tableWidget_3.setCellWidget(row, 3, speed_combo)

                # Color button
                color_button = QtWidgets.QPushButton()
                color_button.setFixedHeight(25)

                if existing_effect and existing_effect.color:
                    color_button.setStyleSheet(f"background-color: {existing_effect.color};")
                    color_button.setText(existing_effect.color)
                else:
                    color_button.setText("Pick Color")

                color_button.clicked.connect(
                    self.create_color_handler(color_button, row, show_part.name, group_name, current_show)
                )
                self.tableWidget_3.setCellWidget(row, 4, color_button)

                # Set row background color based on show part
                qcolor = QtGui.QColor(show_part.color)
                qcolor.setAlpha(40)
                for col in range(5):
                    item = self.tableWidget_3.item(row, col)
                    if item:
                        item.setBackground(qcolor)

                row += 1

    def create_effect_handler(self, row, part_name, group_name, show_name):
        def handle_effect():
            dialog = EffectSelectionDialog(self.main_window.effects_dir, self.main_window)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                effect = dialog.get_selected_effect()
                button = self.tableWidget_3.cellWidget(row, 2)
                if effect == "CLEAR":
                    button.setText("Select Effect")
                else:
                    button.setText(effect)
                self.update_show_effect(show_name, part_name, group_name,
                                        effect or "",
                                        self.get_speed(row),
                                        self.get_color(row))

        return handle_effect

    def create_color_handler(self, button, row, part_name, group_name, show_name):
        def handle_color():
            color = QtWidgets.QColorDialog.getColor(
                initial=QtGui.QColor(button.text() if button.text() != "Pick Color" else "#000000"),
                options=QtWidgets.QColorDialog.ColorDialogOption.ShowAlphaChannel
            )
            if color.isValid():
                hex_color = color.name().upper()
                button.setStyleSheet(f"background-color: {hex_color};")
                button.setText(hex_color)
                self.update_show_effect(show_name, part_name, group_name,
                                        self.get_effect(row),
                                        self.get_speed(row),
                                        hex_color)

        return handle_color

    def get_effect(self, row):
        """Get effect from table row"""
        button = self.tableWidget_3.cellWidget(row, 2)
        return button.text() if button and button.text() != "Select Effect" else ""

    def get_speed(self, row):
        """Get speed from table row"""
        combo = self.tableWidget_3.cellWidget(row, 3)
        return combo.currentText() if combo else "1"

    def get_color(self, row):
        """Get color from table row"""
        button = self.tableWidget_3.cellWidget(row, 4)
        return button.text() if button and button.text() != "Pick Color" else ""

    def update_show_effect(self, show_name, show_part, fixture_group, effect, speed, color):
        """Update show effect in configuration"""
        if show_name not in self.config.shows:
            return

        show = self.config.shows[show_name]
        existing_effect = next(
            (effect_obj for effect_obj in show.effects
             if effect_obj.show_part == show_part
             and effect_obj.fixture_group == fixture_group),
            None
        )

        if existing_effect:
            existing_effect.effect = effect
            existing_effect.speed = speed
            existing_effect.color = color
        else:
            show.effects.append(ShowEffect(
                show_part=show_part,
                fixture_group=fixture_group,
                effect=effect,
                speed=speed,
                color=color
            ))

    def save_show(self):
        """Save current show configuration"""
        try:
            current_show = self.comboBox.currentText()
            if not current_show or current_show not in self.config.shows:
                return

            show = self.config.shows[current_show]

            for row in range(self.tableWidget_3.rowCount()):
                show_part = self.tableWidget_3.item(row, 0).text()
                fixture_group = self.tableWidget_3.item(row, 1).text()
                effect = self.get_effect(row)
                speed = self.get_speed(row)
                color = self.get_color(row)

                self.update_show_effect(current_show, show_part, fixture_group, effect, speed, color)

            print(f"Show {current_show} saved successfully")

        except Exception as e:
            print(f"Error saving show: {e}")
            import traceback
            traceback.print_exc()
