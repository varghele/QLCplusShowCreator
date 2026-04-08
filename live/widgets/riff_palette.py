"""
Riff palette widget — 8 slots for quick riff selection in live mode.
"""

from PyQt6.QtWidgets import QWidget, QGridLayout, QPushButton, QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from typing import List, Optional

from rudiments.registry import get_intensity_rudiments


class RiffPaletteWidget(QWidget):
    """8-slot riff palette with auto-fill and manual override."""

    riff_forced = pyqtSignal(int, str)  # slot_index, rudiment_name

    def __init__(self, parent=None):
        super().__init__(parent)

        self._buttons: List[QPushButton] = []
        self._slot_names: List[Optional[str]] = [None] * 8
        self._active_slot: int = -1

        layout = QGridLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        for i in range(8):
            btn = QPushButton("---")
            btn.setFixedHeight(32)
            btn.setStyleSheet("font-size: 10px; text-align: center;")
            btn.clicked.connect(lambda checked, slot=i: self._on_slot_clicked(slot))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, slot=i: self._on_slot_context_menu(slot)
            )
            row = i // 4
            col = i % 4
            layout.addWidget(btn, row, col)
            self._buttons.append(btn)

    def update_slots(self, rudiment_names: List[str]):
        """Auto-fill slots from engine's top rudiment selections."""
        for i in range(8):
            if i < len(rudiment_names):
                self._slot_names[i] = rudiment_names[i]
                self._buttons[i].setText(rudiment_names[i])
            else:
                self._slot_names[i] = None
                self._buttons[i].setText("---")

        self._update_highlight()

    def set_active_slot(self, index: int):
        """Highlight the currently active riff slot."""
        self._active_slot = index
        self._update_highlight()

    def _on_slot_clicked(self, slot: int):
        name = self._slot_names[slot]
        if name:
            self._active_slot = slot
            self._update_highlight()
            self.riff_forced.emit(slot, name)

    def _on_slot_context_menu(self, slot: int):
        menu = QMenu(self)

        # List all available intensity rudiments
        rudiments = get_intensity_rudiments()
        for name in sorted(rudiments.keys()):
            action = menu.addAction(name)
            action.triggered.connect(
                lambda checked, n=name, s=slot: self._set_slot(s, n)
            )

        # Clear option
        menu.addSeparator()
        clear_action = menu.addAction("Clear override")
        clear_action.triggered.connect(lambda: self._clear_slot(slot))

        menu.exec(self._buttons[slot].mapToGlobal(
            self._buttons[slot].rect().bottomLeft()
        ))

    def _set_slot(self, slot: int, name: str):
        self._slot_names[slot] = name
        self._buttons[slot].setText(name)
        self._active_slot = slot
        self._update_highlight()
        self.riff_forced.emit(slot, name)

    def _clear_slot(self, slot: int):
        # Signal with empty string to clear override
        self.riff_forced.emit(slot, "")

    def _update_highlight(self):
        for i, btn in enumerate(self._buttons):
            if i == self._active_slot:
                btn.setStyleSheet(
                    "font-size: 10px; text-align: center; "
                    "border: 2px solid #4CAF50; background-color: #2E3B2E;"
                )
            else:
                btn.setStyleSheet("font-size: 10px; text-align: center;")
