# gui/tabs/structure_tab.py
# Show structure editing tab with visual timeline

import os
import csv
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QWidget, QLabel,
                             QPushButton, QComboBox, QScrollArea, QFrame,
                             QLineEdit, QSpinBox, QDoubleSpinBox, QColorDialog,
                             QMessageBox, QSplitter, QInputDialog, QSlider,
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QSizePolicy, QMenu, QFileDialog)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QAction
import shutil
from config.models import Configuration, Show, ShowPart, TimelineData
from timeline.song_structure import SongStructure
from timeline_ui import AudioLaneWidget, MasterTimelineContainer
from .base_tab import BaseTab


class TimeSignatureWidget(QWidget):
    """Custom widget for editing time signature with two spinboxes."""

    valueChanged = pyqtSignal(str)  # Emits signature as "4/4" string

    def __init__(self, signature: str = "4/4", parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(2)

        # Parse initial signature
        try:
            num, denom = map(int, signature.split('/'))
        except (ValueError, AttributeError):
            num, denom = 4, 4

        # Numerator spinbox
        self.numerator = QSpinBox()
        self.numerator.setRange(1, 99)
        self.numerator.setValue(num)
        self.numerator.setMaximumWidth(50)
        self.numerator.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.numerator)

        # Separator
        separator = QLabel("/")
        separator.setStyleSheet("color: white;")
        layout.addWidget(separator)

        # Denominator spinbox
        self.denominator = QSpinBox()
        self.denominator.setRange(1, 99)
        self.denominator.setValue(denom)
        self.denominator.setMaximumWidth(50)
        self.denominator.valueChanged.connect(self._on_value_changed)
        layout.addWidget(self.denominator)

        layout.addStretch()

    def _on_value_changed(self):
        """Emit valueChanged signal when either spinbox changes."""
        self.valueChanged.emit(self.get_signature())

    def get_signature(self) -> str:
        """Get current signature as string (e.g., '4/4')."""
        return f"{self.numerator.value()}/{self.denominator.value()}"

    def set_signature(self, signature: str):
        """Set signature from string (e.g., '4/4')."""
        try:
            num, denom = map(int, signature.split('/'))
            self.numerator.blockSignals(True)
            self.denominator.blockSignals(True)
            self.numerator.setValue(num)
            self.denominator.setValue(denom)
            self.numerator.blockSignals(False)
            self.denominator.blockSignals(False)
        except (ValueError, AttributeError):
            pass


class ColorButton(QPushButton):
    """Button that opens color picker and displays current color."""

    colorChanged = pyqtSignal(str)  # Emits color as hex string

    def __init__(self, color: str = "#FFFFFF", parent=None):
        super().__init__(parent)
        self.current_color = QColor(color)
        self.setMinimumHeight(25)
        self.clicked.connect(self._pick_color)
        self._update_style()

    def _pick_color(self):
        """Open color picker dialog."""
        # Temporarily clear stylesheet to avoid affecting dialog
        original_stylesheet = self.styleSheet()
        self.setStyleSheet("")

        color = QColorDialog.getColor(self.current_color, self, "Select Color")

        # Restore stylesheet
        self.setStyleSheet(original_stylesheet)

        if color.isValid():
            self.current_color = color
            self._update_style()
            self.colorChanged.emit(color.name())

    def _update_style(self):
        """Update button background to show current color and display hex value."""
        # Calculate contrasting text color (black or white)
        # Use luminance formula to determine if color is light or dark
        r = self.current_color.red()
        g = self.current_color.green()
        b = self.current_color.blue()
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        text_color = "#000000" if luminance > 0.5 else "#FFFFFF"

        self.setText(self.current_color.name().upper())
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color.name()};
                color: {text_color};
                border: 1px solid #666;
                border-radius: 3px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 2px solid #999;
            }}
        """)

    def get_color(self) -> str:
        """Get current color as hex string."""
        return self.current_color.name()

    def set_color(self, color: str):
        """Set color from hex string."""
        self.current_color = QColor(color)
        self._update_style()


class StructureTab(BaseTab):
    """Tab for editing show structure with visual timeline and audio reference.

    Features:
    - Visual timeline for show parts
    - Audio waveform for alignment
    - Drag-and-drop editing
    - Properties panel for selected part
    - CSV import/export
    - Audio playback
    """

    def __init__(self, config: Configuration, parent=None):
        self.current_show_name = ""
        self.current_show = None

        # Playback state
        self.is_playing = False
        self.playhead_position = 0.0

        # Audio components (lazy init)
        self.audio_engine = None
        self.audio_mixer = None
        self.playback_sync = None
        self.device_manager = None

        # Playback timer
        self.playback_timer = QTimer()
        self.playback_timer.setInterval(16)  # ~60 FPS
        self.playback_timer.timeout.connect(self._update_playback)

        # Flag to prevent recursive activation
        self._is_activating = False

        super().__init__(config, parent)

    def setup_ui(self):
        """Set up the structure tab UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Toolbar
        toolbar = self._create_toolbar()
        main_layout.addLayout(toolbar)

        # Master timeline (very top - shows song structure)
        self.master_timeline = MasterTimelineContainer()
        main_layout.addWidget(self.master_timeline)

        # Audio lane
        self.audio_lane = AudioLaneWidget()
        self.audio_lane.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        main_layout.addWidget(self.audio_lane)

        # Show Structure (table view)
        structure_header = QHBoxLayout()
        structure_label = QLabel("Structure:")
        structure_label.setStyleSheet("font-weight: bold; font-size: 10px; color: #888;")
        structure_header.addWidget(structure_label)

        self.add_part_btn = QPushButton("+ Add Part")
        self.add_part_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        structure_header.addWidget(self.add_part_btn)

        self.delete_part_btn = QPushButton("- Delete Part")
        self.delete_part_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #EF5350;
            }
        """)
        structure_header.addWidget(self.delete_part_btn)

        structure_header.addStretch()
        main_layout.addLayout(structure_header)

        # Create table for show structure
        self.structure_table = QTableWidget()
        self.structure_table.setColumnCount(7)
        self.structure_table.setHorizontalHeaderLabels(["Name", "BPM", "Signature", "Bars", "Duration (s)", "Transition", "Color"])

        # Set column widths
        header = self.structure_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name stretches (but compressed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # BPM
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Signature
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # Bars
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)  # Duration
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)  # Transition
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)  # Color

        # Set minimum column widths
        self.structure_table.setColumnWidth(1, 80)   # BPM
        self.structure_table.setColumnWidth(2, 120)  # Signature
        self.structure_table.setColumnWidth(3, 80)   # Bars
        self.structure_table.setColumnWidth(4, 100)  # Duration
        self.structure_table.setColumnWidth(5, 100)  # Transition
        self.structure_table.setColumnWidth(6, 100)  # Color

        self.structure_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.structure_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.structure_table.setAlternatingRowColors(True)
        self.structure_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.structure_table.customContextMenuRequested.connect(self._show_context_menu)
        self.structure_table.setStyleSheet("""
            QTableWidget {
                background-color: #2a2a2a;
                alternate-background-color: #333333;
                color: white;
                gridline-color: #444444;
            }
            QTableWidget::item:selected {
                background-color: #0078D7;
            }
            QHeaderView::section {
                background-color: #1a1a1a;
                color: white;
                padding: 5px;
                border: 1px solid #444444;
                font-weight: bold;
            }
        """)
        self.structure_table.setMinimumHeight(200)
        # Remove max height to allow table to expand like lanes scroll in Shows tab
        main_layout.addWidget(self.structure_table, 1)  # Takes remaining space

        # Keep reference to song structure for duration calculations
        self.song_structure = None

        # Track current highlighted row for playback
        self.current_highlighted_row = -1

        # Playback controls
        playback_bar = self._create_playback_controls()
        main_layout.addLayout(playback_bar)

    def _create_toolbar(self):
        """Create toolbar with buttons."""
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # Show selector
        show_label = QLabel("Show:")
        show_label.setStyleSheet("font-weight: bold;")
        toolbar.addWidget(show_label)

        self.show_combo = QComboBox()
        self.show_combo.setMinimumWidth(200)
        toolbar.addWidget(self.show_combo)

        # New show button
        self.new_show_btn = QPushButton("+ New")
        self.new_show_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        toolbar.addWidget(self.new_show_btn)

        # Rename show button
        self.rename_show_btn = QPushButton("Rename")
        self.rename_show_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #FFB74D;
            }
        """)
        toolbar.addWidget(self.rename_show_btn)

        # Delete show button
        self.delete_show_btn = QPushButton("Delete Show")
        self.delete_show_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #EF5350;
            }
        """)
        toolbar.addWidget(self.delete_show_btn)

        toolbar.addSpacing(20)

        # Set directory button
        self.set_directory_btn = QPushButton("Set Show Directory")
        self.set_directory_btn.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #AB47BC;
            }
        """)
        toolbar.addWidget(self.set_directory_btn)

        toolbar.addStretch()

        return toolbar

    def _create_playback_controls(self):
        """Create bottom playback control bar."""
        controls = QHBoxLayout()
        controls.setSpacing(10)

        # Playback buttons
        self.play_btn = QPushButton("Play")
        self.play_btn.setFixedWidth(70)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        controls.addWidget(self.play_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #EF5350;
            }
        """)
        controls.addWidget(self.stop_btn)

        controls.addSpacing(20)

        # Time display
        self.time_label = QLabel("00:00.00")
        self.time_label.setStyleSheet("""
            font-family: monospace;
            font-size: 16px;
            font-weight: bold;
            padding: 4px 8px;
            background-color: #333;
            color: #0f0;
            border-radius: 4px;
        """)
        self.time_label.setFixedWidth(100)
        controls.addWidget(self.time_label)

        controls.addSpacing(10)

        # Position slider
        self.position_slider = QSlider(Qt.Orientation.Horizontal)
        self.position_slider.setRange(0, 1000)
        self.position_slider.setValue(0)
        controls.addWidget(self.position_slider, 1)

        # Total time display
        self.total_time_label = QLabel("/ 00:00")
        self.total_time_label.setStyleSheet("font-family: monospace; color: #666;")
        controls.addWidget(self.total_time_label)

        return controls

    def connect_signals(self):
        """Connect widget signals."""
        # Show selection
        self.show_combo.currentTextChanged.connect(self._on_show_changed)

        # Toolbar buttons
        self.new_show_btn.clicked.connect(self._create_new_show)
        self.rename_show_btn.clicked.connect(self._rename_show)
        self.delete_show_btn.clicked.connect(self._delete_show)
        self.set_directory_btn.clicked.connect(self._set_show_directory)

        # Structure header buttons
        self.add_part_btn.clicked.connect(self._add_new_part)
        self.delete_part_btn.clicked.connect(self._delete_part)

        # Table signals
        self.structure_table.itemChanged.connect(self._on_table_cell_changed)

        # Playback controls
        self.play_btn.clicked.connect(self._toggle_playback)
        self.stop_btn.clicked.connect(self._stop_playback)
        self.position_slider.sliderPressed.connect(self._on_position_slider_pressed)
        self.position_slider.sliderReleased.connect(self._on_position_slider_released)
        self.position_slider.valueChanged.connect(self._on_position_slider_changed)

        # Master timeline
        self.master_timeline.scroll_position_changed.connect(self._sync_scroll)
        self.master_timeline.playhead_moved.connect(self._on_playhead_moved)
        self.master_timeline.zoom_changed.connect(self._sync_zoom)

        # Audio lane
        self.audio_lane.audio_file_changed.connect(self._on_audio_file_loaded)
        self.audio_lane.scroll_position_changed.connect(self._sync_scroll)
        self.audio_lane.playhead_moved.connect(self._on_playhead_moved)
        self.audio_lane.zoom_changed.connect(self._sync_zoom)

    def _sync_scroll(self, position: int):
        """Synchronize scroll position across timelines."""
        sender = self.sender()

        # Sync master timeline
        if sender != self.master_timeline:
            self.master_timeline.sync_scroll_position(position)

        # Sync audio lane
        if sender != self.audio_lane:
            self.audio_lane.sync_scroll_position(position)

    def _sync_zoom(self, zoom_factor: float):
        """Synchronize zoom level across all timeline views."""
        sender = self.sender()

        # Sync master timeline
        if sender != self.master_timeline:
            self.master_timeline.set_zoom_factor(zoom_factor)

    def _on_playhead_moved(self, position: float):
        """Handle playhead position change from timeline click."""
        self.playhead_position = position

        # Update master timeline playhead
        self.master_timeline.set_playhead_position(position)

        # Update audio lane playhead
        self.audio_lane.set_playhead_position(position)

    def _recalculate_structure(self):
        """Recalculate timing for all parts."""
        if not self.current_show or not self.current_show.parts:
            self.song_structure = None
            return

        self.song_structure = SongStructure()
        self.song_structure.load_from_show_parts(self.current_show.parts)

    def _populate_table_from_parts(self):
        """Populate table from current show parts."""
        # Block signals while populating
        self.structure_table.blockSignals(True)
        self.structure_table.setRowCount(0)

        if not self.current_show or not self.current_show.parts:
            self.structure_table.blockSignals(False)
            return

        # Recalculate durations
        self._recalculate_structure()

        # Populate table rows
        for part_idx, part in enumerate(self.current_show.parts):
            row = self.structure_table.rowCount()
            self.structure_table.insertRow(row)

            # Name (text field)
            name_item = QTableWidgetItem(part.name)
            self.structure_table.setItem(row, 0, name_item)

            # BPM (double spinbox widget)
            bpm_spinbox = QDoubleSpinBox()
            bpm_spinbox.setRange(1.0, 999.0)
            bpm_spinbox.setDecimals(1)
            bpm_spinbox.setSingleStep(1.0)  # Scroll/arrow increment by 1 BPM
            bpm_spinbox.setValue(part.bpm)
            bpm_spinbox.setStyleSheet("QDoubleSpinBox { background-color: #2a2a2a; color: white; border: 1px solid #444; }")
            bpm_spinbox.valueChanged.connect(lambda value, r=row: self._on_bpm_changed(r, value))
            self.structure_table.setCellWidget(row, 1, bpm_spinbox)

            # Signature (custom widget with two spinboxes)
            sig_widget = TimeSignatureWidget(part.signature)
            sig_widget.valueChanged.connect(lambda sig, r=row: self._on_signature_changed(r, sig))
            self.structure_table.setCellWidget(row, 2, sig_widget)

            # Bars (integer spinbox)
            bars_spinbox = QSpinBox()
            bars_spinbox.setRange(1, 9999)
            bars_spinbox.setValue(part.num_bars)
            bars_spinbox.setStyleSheet("QSpinBox { background-color: #2a2a2a; color: white; border: 1px solid #444; }")
            bars_spinbox.valueChanged.connect(lambda value, r=row: self._on_bars_changed(r, value))
            self.structure_table.setCellWidget(row, 3, bars_spinbox)

            # Duration (read-only text item)
            duration_item = QTableWidgetItem(f"{part.duration:.2f}")
            duration_item.setFlags(duration_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            duration_item.setForeground(QColor(100, 200, 100))  # Light green for read-only
            self.structure_table.setItem(row, 4, duration_item)

            # Transition (combobox widget)
            trans_combo = QComboBox()
            trans_combo.addItems(["instant", "gradual"])
            trans_combo.setCurrentText(part.transition)
            trans_combo.setStyleSheet("QComboBox { background-color: #2a2a2a; color: white; border: 1px solid #444; }")
            trans_combo.currentTextChanged.connect(lambda text, r=row: self._on_transition_changed(r, text))
            self.structure_table.setCellWidget(row, 5, trans_combo)

            # Color (color picker button)
            color_button = ColorButton(part.color)
            color_button.colorChanged.connect(lambda color, r=row: self._on_color_changed(r, color))
            self.structure_table.setCellWidget(row, 6, color_button)

        self.structure_table.blockSignals(False)

    def _add_new_part(self):
        """Add a new part to the current show."""
        if not self.current_show:
            QMessageBox.warning(self, "No Show", "Please create or select a show first.")
            return

        # Create new part with default values
        new_part = ShowPart(
            name=f"Part {len(self.current_show.parts) + 1}",
            color="#4CAF50",
            signature="4/4",
            bpm=120.0,
            num_bars=8,
            transition="instant"
        )

        # Add to show
        self.current_show.parts.append(new_part)

        # Recalculate and refresh table
        self._recalculate_structure()
        self._populate_table_from_parts()

        # Update timelines
        if self.song_structure:
            self.audio_lane.set_song_structure(self.song_structure)
            self.master_timeline.timeline_widget.set_song_structure(self.song_structure)

        # Auto-save
        self._auto_save()

        # Select the new row
        self.structure_table.selectRow(self.structure_table.rowCount() - 1)

    def _on_bpm_changed(self, row: int, value: float):
        """Handle BPM spinbox change."""
        if not self.current_show or row >= len(self.current_show.parts):
            return

        part = self.current_show.parts[row]
        part.bpm = value

        # Recalculate durations and update display
        self._recalculate_structure()
        self._update_duration_cell(row)
        self._update_timelines()
        self._auto_save()

    def _on_signature_changed(self, row: int, signature: str):
        """Handle time signature widget change."""
        if not self.current_show or row >= len(self.current_show.parts):
            return

        part = self.current_show.parts[row]
        part.signature = signature

        # Recalculate durations and update display
        self._recalculate_structure()
        self._update_duration_cell(row)
        self._update_timelines()
        self._auto_save()

    def _on_bars_changed(self, row: int, value: int):
        """Handle bars spinbox change."""
        if not self.current_show or row >= len(self.current_show.parts):
            return

        part = self.current_show.parts[row]
        part.num_bars = value

        # Recalculate durations and update display
        self._recalculate_structure()
        self._update_duration_cell(row)
        self._update_timelines()
        self._auto_save()

    def _on_transition_changed(self, row: int, transition: str):
        """Handle transition combobox change."""
        if not self.current_show or row >= len(self.current_show.parts):
            return

        part = self.current_show.parts[row]
        part.transition = transition
        self._auto_save()

    def _on_color_changed(self, row: int, color: str):
        """Handle color button change."""
        if not self.current_show or row >= len(self.current_show.parts):
            return

        part = self.current_show.parts[row]
        part.color = color

        # Update timelines to reflect new color
        self._update_timelines()
        self._auto_save()

    def _update_duration_cell(self, row: int):
        """Update the duration cell for a specific row."""
        if row >= len(self.current_show.parts):
            return

        part = self.current_show.parts[row]
        duration_item = self.structure_table.item(row, 4)
        if duration_item:
            duration_item.setText(f"{part.duration:.2f}")

    def _update_timelines(self):
        """Update timeline widgets with current song structure."""
        if self.song_structure:
            self.audio_lane.set_song_structure(self.song_structure)
            self.master_timeline.timeline_widget.set_song_structure(self.song_structure)

    def _on_table_cell_changed(self, item):
        """Handle cell edit - only for Name column now (others use custom widgets)."""
        if not self.current_show or item is None:
            return

        row = item.row()
        col = item.column()

        # Only handle Name column (0) - other columns use custom widgets
        if col != 0:
            return

        if row >= len(self.current_show.parts):
            return

        part = self.current_show.parts[row]

        try:
            # Name column
            part.name = item.text()

            # Recalculate durations
            self._recalculate_structure()
            self._update_duration_cell(row)
            self._update_timelines()
            self._auto_save()

        except (ValueError, AttributeError) as e:
            print(f"Invalid cell value: {e}")
            # Revert to previous value
            self._populate_table_from_parts()

    def _update_row_highlight(self):
        """Highlight the row corresponding to current playhead position."""
        if not self.song_structure or not self.current_show:
            return

        # Find which part we're currently in
        current_row = -1
        for i, part in enumerate(self.current_show.parts):
            if part.start_time <= self.playhead_position < part.start_time + part.duration:
                current_row = i
                break

        # Update highlighting if changed
        if current_row != self.current_highlighted_row:
            # Remove old highlighting
            if self.current_highlighted_row >= 0:
                for col in range(self.structure_table.columnCount()):
                    item = self.structure_table.item(self.current_highlighted_row, col)
                    if item:
                        item.setBackground(QColor(42, 42, 42) if self.current_highlighted_row % 2 == 0 else QColor(51, 51, 51))
                        # Restore color column background
                        if col == 6:
                            part = self.current_show.parts[self.current_highlighted_row]
                            item.setBackground(QColor(part.color))

            # Add new highlighting
            if current_row >= 0:
                for col in range(self.structure_table.columnCount()):
                    item = self.structure_table.item(current_row, col)
                    if item:
                        # Highlight with blue
                        if col != 6:  # Don't override color column
                            item.setBackground(QColor(0, 120, 215, 100))

            self.current_highlighted_row = current_row

    def update_from_config(self):
        """Refresh from configuration."""
        # Update show combo
        current = self.show_combo.currentText()
        self.show_combo.blockSignals(True)
        self.show_combo.clear()
        self.show_combo.addItems(sorted(self.config.shows.keys()))

        if current and current in self.config.shows:
            self.show_combo.setCurrentText(current)
        elif self.config.shows:
            self.show_combo.setCurrentIndex(0)

        self.show_combo.blockSignals(False)

        # Load the current show
        self._load_show(self.show_combo.currentText())

    def _on_show_changed(self, show_name):
        """Handle show selection change."""
        self._load_show(show_name)

        # Notify parent to sync with other tabs
        if self.parent() and hasattr(self.parent(), 'on_show_selected'):
            self.parent().on_show_selected(show_name, 'structure')

    def _create_new_show(self):
        """Create a new show with a dialog."""
        # Ensure shows directory is configured
        if not self._ensure_shows_directory():
            return

        name, ok = QInputDialog.getText(
            self,
            "Create New Show",
            "Enter show name:",
            text="New Show"
        )

        if ok and name:
            # Check if name already exists
            if name in self.config.shows:
                QMessageBox.warning(
                    self,
                    "Name Exists",
                    f"A show named '{name}' already exists. Please choose a different name.",
                    QMessageBox.StandardButton.Ok
                )
                return

            # Create new show with default part
            new_show = Show(
                name=name,
                parts=[
                    ShowPart(
                        name="Intro",
                        color="#4CAF50",
                        signature="4/4",
                        bpm=120.0,
                        num_bars=8,
                        transition="instant"
                    )
                ],
                effects=[],
                timeline_data=TimelineData()
            )

            # Add to config
            self.config.shows[name] = new_show

            # Update combo and select new show
            self.show_combo.blockSignals(True)
            self.show_combo.addItem(name)
            self.show_combo.setCurrentText(name)
            self.show_combo.blockSignals(False)

            # Load the new show
            self._load_show(name)

            # Auto-save the new show to CSV
            self._save_to_csv()

            # Notify parent to sync with other tabs
            if self.parent() and hasattr(self.parent(), 'on_show_selected'):
                self.parent().on_show_selected(name, 'structure')

    def _rename_show(self):
        """Rename the current show."""
        if not self.current_show_name:
            QMessageBox.warning(self, "No Show Selected", "Please select a show to rename.")
            return

        old_name = self.current_show_name

        # Get new name from user
        new_name, ok = QInputDialog.getText(
            self,
            "Rename Show",
            "Enter new show name:",
            text=old_name
        )

        if ok and new_name and new_name != old_name:
            # Check if new name already exists
            if new_name in self.config.shows:
                QMessageBox.warning(
                    self,
                    "Name Exists",
                    f"A show named '{new_name}' already exists. Please choose a different name."
                )
                return

            # Rename in config
            self.config.shows[new_name] = self.config.shows.pop(old_name)
            self.config.shows[new_name].name = new_name

            # Rename CSV file
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                shows_dir = os.path.join(project_root, "shows")
                old_csv = os.path.join(shows_dir, f"{old_name}.csv")
                new_csv = os.path.join(shows_dir, f"{new_name}.csv")

                if os.path.exists(old_csv):
                    os.rename(old_csv, new_csv)
            except Exception as e:
                print(f"Failed to rename CSV file: {e}")

            # Update current show name
            self.current_show_name = new_name

            # Update dropdown
            self.show_combo.blockSignals(True)
            self.show_combo.clear()
            self.show_combo.addItems(sorted(self.config.shows.keys()))
            self.show_combo.setCurrentText(new_name)
            self.show_combo.blockSignals(False)

            # Notify parent to sync
            if self.parent() and hasattr(self.parent(), 'on_show_selected'):
                self.parent().on_show_selected(new_name, 'structure')

            QMessageBox.information(self, "Success", f"Show renamed from '{old_name}' to '{new_name}'.")

    def _set_show_directory(self):
        """Manually set/change the shows directory."""
        # Ask user to choose directory
        current_dir = self.config.shows_directory if self.config.shows_directory else os.path.expanduser("~")

        custom_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Shows Directory",
            current_dir,
            QFileDialog.Option.ShowDirsOnly
        )

        if custom_dir:
            self.config.shows_directory = custom_dir

            # Create audiofiles subdirectory
            audiofiles_dir = os.path.join(self.config.shows_directory, "audiofiles")
            os.makedirs(audiofiles_dir, exist_ok=True)

            # Auto-load shows and refresh
            self._auto_load_shows()
            self.update_from_config()

            QMessageBox.information(
                self,
                "Directory Set",
                f"Shows directory set to:\n{custom_dir}\n\nLoaded {len(self.config.shows)} show(s)."
            )

    def _ensure_shows_directory(self) -> bool:
        """Ensure shows directory is configured. Returns True if set, False if cancelled."""
        if self.config.shows_directory and os.path.exists(self.config.shows_directory):
            return True

        print(f"DEBUG: No shows directory set, prompting user...")

        # Ask user if they want to use default or choose custom directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        default_dir = os.path.join(project_root, "shows")

        reply = QMessageBox.question(
            self,
            "Set Shows Directory",
            f"No shows directory is configured.\n\n"
            f"Default location: {default_dir}\n\n"
            f"WARNING: The default location is in the program directory and may be overwritten during updates.\n"
            f"It's recommended to choose your own directory.\n\n"
            f"Do you want to use the default location?\n"
            f"(Click 'No' to choose a custom directory)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )

        if reply == QMessageBox.StandardButton.Cancel:
            return False
        elif reply == QMessageBox.StandardButton.Yes:
            # Use default directory
            os.makedirs(default_dir, exist_ok=True)
            self.config.shows_directory = default_dir
        else:
            # Choose custom directory
            custom_dir = QFileDialog.getExistingDirectory(
                self,
                "Select Shows Directory",
                os.path.expanduser("~"),
                QFileDialog.Option.ShowDirsOnly
            )
            if not custom_dir:
                return False
            self.config.shows_directory = custom_dir

        # Create audiofiles subdirectory
        audiofiles_dir = os.path.join(self.config.shows_directory, "audiofiles")
        os.makedirs(audiofiles_dir, exist_ok=True)

        # Auto-load shows from the newly configured directory
        self._auto_load_shows()

        return True

    def _delete_show(self):
        """Delete the current show (from config and disk)."""
        if not self.current_show_name:
            QMessageBox.warning(self, "No Show Selected", "Please select a show to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete show '{self.current_show_name}'?\n\n"
            f"This will delete:\n"
            f"- The show configuration\n"
            f"- The CSV file\n"
            f"- Associated audio files\n\n"
            f"This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        show = self.config.shows.get(self.current_show_name)

        # Delete CSV file
        if self.config.shows_directory:
            csv_path = os.path.join(self.config.shows_directory, f"{self.current_show_name}.csv")
            if os.path.exists(csv_path):
                try:
                    os.remove(csv_path)
                except Exception as e:
                    print(f"Failed to delete CSV file: {e}")

            # Delete audio file if it exists
            if show and show.timeline_data and show.timeline_data.audio_file_path:
                audio_filename = os.path.basename(show.timeline_data.audio_file_path)
                audio_path = os.path.join(self.config.shows_directory, "audiofiles", audio_filename)
                if os.path.exists(audio_path):
                    try:
                        os.remove(audio_path)
                    except Exception as e:
                        print(f"Failed to delete audio file: {e}")

        # Delete from config
        del self.config.shows[self.current_show_name]

        # Clear UI
        self.current_show_name = ""
        self.current_show = None

        # Refresh dropdown
        self.show_combo.blockSignals(True)
        self.show_combo.clear()
        self.show_combo.addItems(sorted(self.config.shows.keys()))
        if self.config.shows:
            self.show_combo.setCurrentIndex(0)
        self.show_combo.blockSignals(False)

        # Load first show if available
        if self.show_combo.currentText():
            self._load_show(self.show_combo.currentText())
        else:
            self._clear_timeline()

        QMessageBox.information(self, "Success", "Show deleted successfully.")

    def _auto_load_shows(self):
        """Automatically load all shows from the configured directory."""
        if not self.config.shows_directory or not os.path.exists(self.config.shows_directory):
            print(f"DEBUG: Cannot auto-load - no valid directory (directory={self.config.shows_directory})")
            return

        print(f"DEBUG: Auto-loading shows from {self.config.shows_directory}")
        try:
            self._import_all_shows_from_csv()
            print(f"DEBUG: Import completed, shows: {list(self.config.shows.keys())}")
        except Exception as e:
            print(f"Failed to auto-load shows: {e}")
            import traceback
            traceback.print_exc()

    def _clear_timeline(self):
        """Clear the timeline and table."""
        self.structure_table.setRowCount(0)
        self.audio_lane.set_song_structure(None)
        self.master_timeline.timeline_widget.set_song_structure(None)

    def _load_show(self, show_name):
        """Load a show for editing."""
        if not show_name or show_name not in self.config.shows:
            self.current_show_name = ""
            self.current_show = None
            self.structure_table.setRowCount(0)
            self.audio_lane.set_song_structure(None)
            self.master_timeline.timeline_widget.set_song_structure(None)
            return

        self.current_show_name = show_name
        self.current_show = self.config.shows[show_name]

        # Populate table from parts
        self._populate_table_from_parts()

        # Set song structure on both audio lane and master timeline
        if self.song_structure:
            self.audio_lane.set_song_structure(self.song_structure)
            self.master_timeline.timeline_widget.set_song_structure(self.song_structure)

        # Load audio if available, or clear if not
        if self.current_show.timeline_data and self.current_show.timeline_data.audio_file_path:
            audio_filename = self.current_show.timeline_data.audio_file_path

            # Check if it's just a filename (new format) or a full path (old format)
            if not os.path.isabs(audio_filename):
                # New format: filename only, look in audiofiles folder
                if self.config.shows_directory:
                    audio_path = os.path.join(self.config.shows_directory, "audiofiles", audio_filename)
                    if os.path.exists(audio_path):
                        self.audio_lane.load_audio_file(audio_path)
                    else:
                        print(f"Audio file not found: {audio_path}")
                        self.audio_lane.clear_audio()
            else:
                # Old format: full path
                if os.path.exists(audio_filename):
                    self.audio_lane.load_audio_file(audio_filename)
                else:
                    print(f"Audio file not found: {audio_filename}")
                    self.audio_lane.clear_audio()
        else:
            # No audio for this show, clear it
            self.audio_lane.clear_audio()


    def _load_all_shows(self):
        """Load all shows from CSV files in the shows directory."""
        try:
            # Import all shows
            self._import_all_shows_from_csv()

            # Update dropdown
            self.update_from_config()

            # Show success message
            show_count = len(self.config.shows)
            QMessageBox.information(
                self,
                "Success",
                f"Loaded {show_count} show(s) from CSV files."
            )

            # Load first show if available
            if self.show_combo.count() > 0:
                self._load_show(self.show_combo.currentText())

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load shows:\n{str(e)}"
            )

    def _delete_part(self):
        """Delete the selected part."""
        current_row = self.structure_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a part to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Are you sure you want to delete this part?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Delete from show parts
            del self.current_show.parts[current_row]

            # Recalculate and refresh
            self._recalculate_structure()
            self._populate_table_from_parts()

            # Update timelines
            if self.song_structure:
                self.audio_lane.set_song_structure(self.song_structure)
                self.master_timeline.timeline_widget.set_song_structure(self.song_structure)

            self._auto_save()

    def _show_context_menu(self, position):
        """Show context menu for table right-click."""
        menu = QMenu(self)

        # Add Part action
        add_action = QAction("Add Part", self)
        add_action.triggered.connect(self._add_new_part)
        menu.addAction(add_action)

        # Delete Part action (only if a row is selected)
        current_row = self.structure_table.currentRow()
        if current_row >= 0:
            delete_action = QAction("Delete Selected Part", self)
            delete_action.triggered.connect(self._delete_part)
            menu.addAction(delete_action)

        # Show menu at cursor position
        menu.exec(self.structure_table.viewport().mapToGlobal(position))

    def _import_from_csv(self):
        """Import show structure from CSV file."""
        if not self.current_show_name:
            QMessageBox.warning(self, "No Show Selected", "Please select a show first.")
            return

        # Use the existing import functionality
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        csv_path = os.path.join(project_root, "shows", f"{self.current_show_name}.csv")

        if not os.path.exists(csv_path):
            QMessageBox.warning(
                self,
                "CSV Not Found",
                f"No CSV file found for show '{self.current_show_name}' at:\n{csv_path}"
            )
            return

        try:
            # Clear existing parts
            self.current_show.parts.clear()

            # Read CSV
            with open(csv_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    part = ShowPart(
                        name=row['showpart'],
                        color=row['color'],
                        signature=row['signature'],
                        bpm=float(row['bpm']),
                        num_bars=int(row['num_bars']),
                        transition=row['transition']
                    )
                    self.current_show.parts.append(part)

            # Reload display
            self._populate_table_from_parts()

            # Update timelines
            if self.song_structure:
                self.audio_lane.set_song_structure(self.song_structure)
                self.master_timeline.timeline_widget.set_song_structure(self.song_structure)

            QMessageBox.information(self, "Success", f"Imported {len(self.current_show.parts)} parts from CSV.")

        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import CSV:\n{str(e)}")

    def _auto_save(self):
        """Auto-save to config and CSV."""
        if not self.current_show_name or not self.current_show:
            return

        # Save to config (already updated in memory)
        # Save to CSV
        self._save_to_csv()

    def _save_to_csv(self):
        """Save current show structure to CSV file."""
        if not self.current_show or not self.current_show.parts:
            return

        # Ensure shows directory is configured
        if not self._ensure_shows_directory():
            return

        csv_path = os.path.join(self.config.shows_directory, f"{self.current_show_name}.csv")

        try:
            with open(csv_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['showpart', 'signature', 'bpm', 'num_bars', 'transition', 'color'])
                writer.writeheader()

                for part in self.current_show.parts:
                    writer.writerow({
                        'showpart': part.name,
                        'signature': part.signature,
                        'bpm': part.bpm,
                        'num_bars': part.num_bars,
                        'transition': part.transition,
                        'color': part.color
                    })
        except Exception as e:
            print(f"Failed to save CSV: {e}")

    def _import_all_shows_from_csv(self):
        """Import all show structures from CSV files in the shows directory."""
        # Use configured shows directory
        if not self.config.shows_directory:
            return

        shows_dir = self.config.shows_directory

        # Check if shows directory exists
        if not os.path.exists(shows_dir):
            print(f"Shows directory not found: {shows_dir}")
            return

        # Scan for all show structure CSV files
        csv_files = [f for f in os.listdir(shows_dir) if f.endswith('.csv')]

        if not csv_files:
            print(f"No CSV files found in {shows_dir}")
            return

        imported_count = 0

        for file in csv_files:
            try:
                show_name = os.path.splitext(file)[0]  # Remove .csv extension
                structure_file = os.path.join(shows_dir, file)

                # Check if show already exists in configuration
                if show_name in self.config.shows:
                    show = self.config.shows[show_name]
                    # Clear existing parts to reload from CSV
                    show.parts.clear()
                else:
                    # Create new Show object with timeline data
                    show = Show(
                        name=show_name,
                        parts=[],
                        effects=[],
                        timeline_data=TimelineData()
                    )
                    self.config.shows[show_name] = show

                # Read CSV and create show parts
                with open(structure_file, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        # Create ShowPart from CSV row
                        show_part = ShowPart(
                            name=row['showpart'],
                            color=row['color'],
                            signature=row['signature'],
                            bpm=float(row['bpm']),
                            num_bars=int(row['num_bars']),
                            transition=row['transition']
                        )
                        # Add part to show
                        show.parts.append(show_part)

                imported_count += 1
                print(f"Imported show: {show_name}")

            except Exception as e:
                print(f"Failed to import {file}: {e}")

        print(f"Successfully imported {imported_count} show(s) from {shows_dir}")

    def _on_audio_file_loaded(self, file_path: str):
        """Handle audio file loaded - copy to audiofiles folder."""
        if not file_path or not self.current_show:
            return

        # Ensure shows directory is configured
        if not self._ensure_shows_directory():
            return

        # Copy audio file to audiofiles folder
        try:
            audiofiles_dir = os.path.join(self.config.shows_directory, "audiofiles")
            os.makedirs(audiofiles_dir, exist_ok=True)

            filename = os.path.basename(file_path)
            dest_path = os.path.join(audiofiles_dir, filename)

            # Copy file if it's not already in audiofiles directory
            if os.path.abspath(file_path) != os.path.abspath(dest_path):
                shutil.copy2(file_path, dest_path)
                print(f"Copied audio file to: {dest_path}")

            # Store just the filename in timeline_data
            if self.current_show.timeline_data is None:
                self.current_show.timeline_data = TimelineData()
            self.current_show.timeline_data.audio_file_path = filename

            self._auto_save()

        except Exception as e:
            QMessageBox.warning(
                self,
                "Audio Copy Error",
                f"Failed to copy audio file to shows directory:\n{str(e)}"
            )

        # Update time display
        if self.song_structure:
            total_duration = self.song_structure.get_total_duration()
            self.total_time_label.setText(f"/ {self._format_time(total_duration)}")

    def _toggle_playback(self):
        """Toggle play/pause."""
        if self.is_playing:
            self._pause_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        """Start playback."""
        if not self.song_structure:
            return

        self.is_playing = True
        self.play_btn.setText("Pause")

        # Initialize audio if available
        try:
            from audio.audio_file import AudioFile
            from audio.audio_engine import AudioEngine
            from audio.audio_mixer import AudioMixer
            from audio.playback_synchronizer import PlaybackSynchronizer
            from audio.device_manager import DeviceManager

            if self.audio_lane.get_audio_file():
                self._init_audio_engine()
                if self.playback_sync:
                    self.playback_sync.on_play_requested(self.playhead_position)
        except ImportError:
            pass  # Audio not available

        self.playback_timer.start()

    def _pause_playback(self):
        """Pause playback."""
        self.is_playing = False
        self.play_btn.setText("Play")
        self.playback_timer.stop()

        if self.playback_sync:
            self.playback_sync.on_pause_requested()

    def _stop_playback(self):
        """Stop playback and reset position."""
        self.is_playing = False
        self.play_btn.setText("Play")
        self.playback_timer.stop()

        if self.playback_sync:
            self.playback_sync.on_stop_requested()

        self.playhead_position = 0.0
        self.time_label.setText("00:00.00")
        self.position_slider.setValue(0)

    def _update_playback(self):
        """Called by timer during playback to update position."""
        if not self.is_playing or not self.song_structure:
            return

        # Get position from audio if available, otherwise use timer
        if self.playback_sync:
            position = self.playback_sync.get_accurate_position()
        else:
            # Fallback: increment by timer interval
            position = self.playhead_position + 0.016  # 16ms

        total = self.song_structure.get_total_duration()
        if position >= total:
            self._stop_playback()
            return

        self.playhead_position = position
        self.time_label.setText(self._format_time(position))

        # Update position slider
        if total > 0:
            slider_pos = int((position / total) * 1000)
            self.position_slider.blockSignals(True)
            self.position_slider.setValue(slider_pos)
            self.position_slider.blockSignals(False)

        # Update playhead on all timelines
        self.master_timeline.set_playhead_position(position)
        self.audio_lane.set_playhead_position(position)

        # Update table row highlighting
        self._update_row_highlight()

    def _on_position_slider_pressed(self):
        """Handle position slider press - pause updates during drag."""
        self._slider_dragging = True

    def _on_position_slider_released(self):
        """Handle position slider release - seek to position."""
        self._slider_dragging = False
        if self.song_structure:
            total = self.song_structure.get_total_duration()
            position = (self.position_slider.value() / 1000.0) * total
            self.playhead_position = position
            if self.playback_sync:
                self.playback_sync.on_seek_requested(position)

    def _on_position_slider_changed(self, value: int):
        """Handle position slider value change during drag."""
        if hasattr(self, '_slider_dragging') and self._slider_dragging:
            if self.song_structure:
                total = self.song_structure.get_total_duration()
                position = (value / 1000.0) * total
                self.time_label.setText(self._format_time(position))

    def _format_time(self, seconds: float) -> str:
        """Format time as MM:SS.ss"""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes:02d}:{secs:05.2f}"

    def _init_audio_engine(self):
        """Initialize audio engine on first use."""
        try:
            from audio.audio_file import AudioFile
            from audio.audio_engine import AudioEngine
            from audio.audio_mixer import AudioMixer
            from audio.playback_synchronizer import PlaybackSynchronizer
            from audio.device_manager import DeviceManager

            if self.audio_engine is None:
                self.device_manager = DeviceManager()
                self.audio_engine = AudioEngine()
                self.audio_mixer = AudioMixer()

                # Apply stored audio settings if available from parent
                device_index = None
                if hasattr(self.parent(), 'audio_settings') and self.parent().audio_settings:
                    device_index = self.parent().audio_settings.get('device_index')
                    sample_rate = self.parent().audio_settings.get('sample_rate', 44100)
                    buffer_size = self.parent().audio_settings.get('buffer_size', 1024)
                    self.audio_engine.sample_rate = sample_rate
                    self.audio_engine.buffer_size = buffer_size

                # Initialize audio engine with device
                self.audio_engine.initialize(device_index=device_index)

                self.playback_sync = PlaybackSynchronizer(
                    self.audio_engine, self.audio_mixer
                )

                # Load audio file into mixer
                audio_file = self.audio_lane.get_audio_file()
                if audio_file:
                    self.audio_mixer.add_lane("audio", audio_file, 1.0)

                # Connect volume/mute if available
                if hasattr(self.audio_lane, 'volume_slider'):
                    self.audio_lane.volume_slider.valueChanged.connect(
                        lambda v: self.audio_mixer.update_lane_volume("audio", v / 100.0) if self.audio_mixer else None
                    )
                if hasattr(self.audio_lane, 'mute_button'):
                    self.audio_lane.mute_button.toggled.connect(
                        lambda m: self.audio_mixer.set_mute_state("audio", m) if self.audio_mixer else None
                    )

        except Exception as e:
            print(f"Failed to initialize audio engine: {e}")
            self.audio_engine = None
            self.playback_sync = None

    def save_to_config(self):
        """Save to configuration (already saved via auto-save)."""
        pass

    def on_tab_activated(self):
        """Called when tab becomes visible."""
        # Prevent recursive activation
        if self._is_activating:
            print("DEBUG: Skipping recursive activation")
            return

        try:
            self._is_activating = True
            print(f"DEBUG: Structure tab activated, shows_directory = {self.config.shows_directory}")

            # Ensure shows directory is configured on first activation
            if not self.config.shows_directory or not os.path.exists(self.config.shows_directory):
                print("DEBUG: Prompting for shows directory...")
                if not self._ensure_shows_directory():
                    print("DEBUG: User cancelled directory selection")
                    return  # User cancelled, don't proceed

            # Auto-load shows and refresh the dropdown
            print("DEBUG: Auto-loading shows...")
            self._auto_load_shows()
            print(f"DEBUG: After auto-load, config.shows has {len(self.config.shows)} shows")
            print(f"DEBUG: Shows: {list(self.config.shows.keys())}")
            self.update_from_config()
        except Exception as e:
            print(f"ERROR in on_tab_activated: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self._is_activating = False

    def on_tab_deactivated(self):
        """Called when leaving tab."""
        self._pause_playback()  # Pause when leaving tab

    def cleanup(self):
        """Clean up audio resources."""
        self._stop_playback()

        if self.audio_engine:
            try:
                self.audio_engine.shutdown()
            except Exception:
                pass
            self.audio_engine = None
            self.audio_mixer = None
            self.playback_sync = None
