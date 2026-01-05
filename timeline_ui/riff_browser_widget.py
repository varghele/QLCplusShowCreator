# timeline_ui/riff_browser_widget.py
"""RiffBrowserWidget - Dockable panel for browsing and selecting riffs."""

import json
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QTreeWidget, QTreeWidgetItem, QPushButton,
    QLabel, QFrame, QSizePolicy, QStackedWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QDrag, QPixmap, QPainter, QColor, QFont

from config.models import Riff, FixtureGroup
from riffs.riff_library import RiffLibrary


class RiffItemWidget(QFrame):
    """Widget representing a single riff in the browser."""

    def __init__(self, riff: Riff, parent=None):
        super().__init__(parent)
        self.riff = riff
        self._setup_ui()
        self.setAcceptDrops(False)

    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            RiffItemWidget {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
            RiffItemWidget:hover {
                background-color: #4a4a4a;
                border-color: #777;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        # Riff name
        name_label = QLabel(self.riff.name.replace('_', ' ').title())
        name_label.setStyleSheet("font-weight: bold; color: #fff;")
        layout.addWidget(name_label)

        # Info line: beats | fixture type
        info_parts = []
        beats = int(self.riff.length_beats)
        bars = beats // 4
        if bars > 0:
            info_parts.append(f"{bars} bar{'s' if bars > 1 else ''}")
        else:
            info_parts.append(f"{beats} beat{'s' if beats > 1 else ''}")

        if self.riff.fixture_types:
            info_parts.append(" | ".join(self.riff.fixture_types))
        else:
            info_parts.append("Universal")

        info_label = QLabel(" | ".join(info_parts))
        info_label.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(info_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not hasattr(self, '_drag_start_pos'):
            return

        # Check if we've moved enough to start a drag
        if (event.pos() - self._drag_start_pos).manhattanLength() < 10:
            return

        # Start drag
        drag = QDrag(self)
        mime_data = QMimeData()

        # Serialize riff reference
        riff_data = {
            "path": f"{self.riff.category}/{self.riff.name}",
            "name": self.riff.name,
            "length_beats": self.riff.length_beats
        }
        mime_data.setData("application/x-qlc-riff", json.dumps(riff_data).encode())

        drag.setMimeData(mime_data)

        # Create drag pixmap
        pixmap = self._create_drag_pixmap()
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())

        drag.exec(Qt.DropAction.CopyAction)

    def _create_drag_pixmap(self) -> QPixmap:
        """Create a simple pixmap for drag preview."""
        width = 120
        height = 30
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor(60, 60, 60, 200))

        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Arial", 9))

        # Draw riff name
        text = self.riff.name.replace('_', ' ')
        if len(text) > 15:
            text = text[:12] + "..."
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)

        painter.end()
        return pixmap


class CollapsedRiffBar(QWidget):
    """Thin vertical bar shown when riff browser is collapsed."""

    expand_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedWidth(28)
        self.setStyleSheet("""
            CollapsedRiffBar {
                background-color: #2d2d2d;
                border-left: 1px solid #555;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)
        layout.setSpacing(4)

        # Expand button at top
        self.expand_btn = QPushButton("◀")
        self.expand_btn.setFixedSize(24, 24)
        self.expand_btn.setToolTip("Expand Riff Library")
        self.expand_btn.clicked.connect(self.expand_clicked.emit)
        self.expand_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 4px;
                color: #fff;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
                border-color: #777;
            }
        """)
        layout.addWidget(self.expand_btn)

        # Vertical label
        self.label = QLabel("R\ni\nf\nf\ns")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("""
            color: #888;
            font-size: 11px;
            font-weight: bold;
        """)
        layout.addWidget(self.label)

        layout.addStretch()


class RiffBrowserWidget(QDockWidget):
    """Dockable panel for browsing and selecting riffs."""

    # Signal emitted when a riff drag starts (for UI feedback)
    riff_drag_started = pyqtSignal(object)  # Riff object

    def __init__(self, riff_library: RiffLibrary = None, parent=None):
        super().__init__("Riff Library", parent)

        self.riff_library = riff_library or RiffLibrary()
        self._fixture_filter: FixtureGroup = None
        self._category_items: dict = {}  # category name -> QTreeWidgetItem
        self._is_collapsed = False

        self._setup_ui()
        self._populate_tree()

    def _setup_ui(self):
        """Create the browser UI."""
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )

        # Use stacked widget to switch between expanded and collapsed views
        self._stacked = QStackedWidget()
        self.setWidget(self._stacked)

        # Expanded view (full browser)
        self._expanded_widget = QWidget()
        self._setup_expanded_ui()
        self._stacked.addWidget(self._expanded_widget)

        # Collapsed view (thin bar)
        self._collapsed_bar = CollapsedRiffBar()
        self._collapsed_bar.expand_clicked.connect(self.expand)
        self._stacked.addWidget(self._collapsed_bar)

        # Start expanded
        self._stacked.setCurrentIndex(0)
        self._update_size_for_state()

    def _setup_expanded_ui(self):
        """Set up the expanded (full) UI."""
        layout = QVBoxLayout(self._expanded_widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header with collapse and refresh buttons
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)

        # Collapse button
        self._collapse_btn = QPushButton("▶")
        self._collapse_btn.setFixedSize(24, 24)
        self._collapse_btn.setToolTip("Collapse Riff Library")
        self._collapse_btn.clicked.connect(self.collapse)
        self._collapse_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 4px;
                color: #fff;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        header_layout.addWidget(self._collapse_btn)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search riffs...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
                color: #fff;
            }
            QLineEdit:focus {
                border-color: #0078d4;
            }
        """)
        header_layout.addWidget(self.search_input, 1)

        # Refresh button
        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setToolTip("Refresh riff library")
        refresh_btn.clicked.connect(self._on_refresh)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 4px;
                color: #fff;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
        """)
        header_layout.addWidget(refresh_btn)

        layout.addLayout(header_layout)

        # Category tree
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        self.tree.setAnimated(True)
        self.tree.setExpandsOnDoubleClick(True)
        self.tree.setDragEnabled(False)  # We handle drag manually
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #2d2d2d;
                border: 1px solid #555;
                border-radius: 4px;
                color: #fff;
            }
            QTreeWidget::item {
                padding: 2px 0;
            }
            QTreeWidget::item:hover {
                background-color: #3c3c3c;
            }
            QTreeWidget::item:selected {
                background-color: #0078d4;
            }
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {
                image: url(none);
                border-image: none;
            }
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {
                image: url(none);
                border-image: none;
            }
        """)
        layout.addWidget(self.tree, 1)

        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label)

        self._update_status()

    def _update_size_for_state(self):
        """Update widget size based on collapsed state."""
        if self._is_collapsed:
            self.setMinimumWidth(28)
            self.setMaximumWidth(28)
        else:
            self.setMinimumWidth(200)
            self.setMaximumWidth(16777215)  # QWIDGETSIZE_MAX

    def collapse(self):
        """Collapse the riff browser to a thin bar."""
        if self._is_collapsed:
            return
        self._is_collapsed = True
        self._stacked.setCurrentIndex(1)
        self._update_size_for_state()
        # Hide title bar when collapsed
        self.setTitleBarWidget(QWidget())

    def expand(self):
        """Expand the riff browser to full view."""
        if not self._is_collapsed:
            return
        self._is_collapsed = False
        self._stacked.setCurrentIndex(0)
        self._update_size_for_state()
        # Restore title bar
        self.setTitleBarWidget(None)

    def is_collapsed(self) -> bool:
        """Return whether the browser is currently collapsed."""
        return self._is_collapsed

    def set_collapsed(self, collapsed: bool):
        """Set the collapsed state."""
        if collapsed:
            self.collapse()
        else:
            self.expand()

    def _populate_tree(self):
        """Populate the tree with categories and riffs."""
        self.tree.clear()
        self._category_items.clear()

        # Category icons/prefixes
        category_icons = {
            "builds": "📈",
            "fills": "⚡",
            "loops": "🔄",
            "drops": "💥",
            "movement": "↔️",
            "custom": "⭐"
        }

        for category in self.riff_library.get_categories():
            riffs = self.riff_library.get_riffs_in_category(category)

            # Filter by fixture compatibility if set
            if self._fixture_filter:
                riffs = [r for r in riffs
                         if r.is_compatible_with(self._fixture_filter)[0]]

            # Skip empty categories
            if not riffs:
                continue

            # Create category item
            icon = category_icons.get(category, "📁")
            category_item = QTreeWidgetItem([f"{icon} {category.title()} ({len(riffs)})"])
            category_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "category", "name": category})
            self._category_items[category] = category_item
            self.tree.addTopLevelItem(category_item)

            # Add riff items
            for riff in riffs:
                riff_item = QTreeWidgetItem()
                riff_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "riff", "riff": riff})

                # Create custom widget for riff
                widget = RiffItemWidget(riff)
                riff_item.setSizeHint(0, widget.sizeHint())

                category_item.addChild(riff_item)
                self.tree.setItemWidget(riff_item, 0, widget)

        # Expand all categories by default
        self.tree.expandAll()

    def _on_search_changed(self, text: str):
        """Filter riffs based on search text."""
        search_lower = text.lower().strip()

        if not search_lower:
            # Show all
            self._populate_tree()
            return

        # Search and repopulate
        self.tree.clear()
        self._category_items.clear()

        results = self.riff_library.search(search_lower, self._fixture_filter)

        if not results:
            self.status_label.setText("No riffs found")
            return

        # Group results by category
        by_category = {}
        for riff in results:
            if riff.category not in by_category:
                by_category[riff.category] = []
            by_category[riff.category].append(riff)

        # Create tree items
        category_icons = {
            "builds": "📈",
            "fills": "⚡",
            "loops": "🔄",
            "drops": "💥",
            "movement": "↔️",
            "custom": "⭐"
        }

        for category, riffs in sorted(by_category.items()):
            icon = category_icons.get(category, "📁")
            category_item = QTreeWidgetItem([f"{icon} {category.title()} ({len(riffs)})"])
            self._category_items[category] = category_item
            self.tree.addTopLevelItem(category_item)

            for riff in riffs:
                riff_item = QTreeWidgetItem()
                riff_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "riff", "riff": riff})

                widget = RiffItemWidget(riff)
                riff_item.setSizeHint(0, widget.sizeHint())

                category_item.addChild(riff_item)
                self.tree.setItemWidget(riff_item, 0, widget)

        self.tree.expandAll()
        self._update_status(f"Found {len(results)} riff(s)")

    def _on_refresh(self):
        """Reload riffs from disk."""
        self.riff_library.refresh()
        self._populate_tree()
        self._update_status()

    def _update_status(self, message: str = None):
        """Update status label."""
        if message:
            self.status_label.setText(message)
        else:
            count = len(self.riff_library)
            self.status_label.setText(f"{count} riff{'s' if count != 1 else ''} available")

    def set_fixture_filter(self, fixture_group: FixtureGroup):
        """Filter to show only compatible riffs.

        Args:
            fixture_group: Group to filter by, or None to show all
        """
        self._fixture_filter = fixture_group
        self._populate_tree()

        if fixture_group:
            self._update_status(f"Showing riffs for: {fixture_group.name}")
        else:
            self._update_status()

    def clear_fixture_filter(self):
        """Clear fixture filter and show all riffs."""
        self.set_fixture_filter(None)

    def get_riff_library(self) -> RiffLibrary:
        """Get the riff library instance."""
        return self.riff_library
