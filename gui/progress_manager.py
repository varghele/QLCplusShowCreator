# gui/progress_manager.py
# Progress indicator management for long-running operations

from PyQt6.QtWidgets import QProgressDialog, QApplication, QStatusBar, QProgressBar, QLabel, QWidget, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer


class StatusBarProgress(QWidget):
    """Progress indicator widget for status bar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.label = QLabel()
        self.label.setStyleSheet("color: #888;")
        layout.addWidget(self.label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(150)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        layout.addWidget(self.progress_bar)

        self.hide()

    def start(self, message: str, maximum: int = 0):
        """Start showing progress.

        Args:
            message: Status message to display
            maximum: Maximum value (0 for indeterminate)
        """
        self.label.setText(message)
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(0)
        self.show()
        QApplication.processEvents()

    def update(self, value: int = None, message: str = None):
        """Update progress.

        Args:
            value: Current progress value (None to increment by 1)
            message: Optional new message
        """
        if message:
            self.label.setText(message)
        if value is not None:
            self.progress_bar.setValue(value)
        elif self.progress_bar.maximum() > 0:
            self.progress_bar.setValue(self.progress_bar.value() + 1)
        QApplication.processEvents()

    def finish(self):
        """Hide the progress indicator."""
        self.hide()
        self.label.setText("")
        self.progress_bar.setValue(0)


class ProgressManager:
    """
    Manages progress indicators throughout the application.

    Provides both status bar progress (non-blocking) and modal dialogs (blocking).
    """

    def __init__(self, main_window=None):
        """Initialize progress manager.

        Args:
            main_window: Main application window (for status bar access)
        """
        self.main_window = main_window
        self.status_progress = None
        self.modal_dialog = None

        # Set up status bar progress widget
        if main_window and hasattr(main_window, 'statusBar'):
            self.status_progress = StatusBarProgress()
            main_window.statusBar().addPermanentWidget(self.status_progress)

    def start_status(self, message: str, maximum: int = 0):
        """Start status bar progress indicator.

        Args:
            message: Status message
            maximum: Maximum value (0 for indeterminate/busy indicator)
        """
        if self.status_progress:
            self.status_progress.start(message, maximum)

    def update_status(self, value: int = None, message: str = None):
        """Update status bar progress.

        Args:
            value: Current value (None to auto-increment)
            message: Optional new message
        """
        if self.status_progress:
            self.status_progress.update(value, message)

    def finish_status(self):
        """Finish status bar progress."""
        if self.status_progress:
            self.status_progress.finish()

    def start_modal(self, title: str, message: str, maximum: int = 0,
                    cancelable: bool = False, parent=None) -> QProgressDialog:
        """Start a modal progress dialog.

        Args:
            title: Dialog title
            message: Progress message
            maximum: Maximum value (0 for indeterminate)
            cancelable: Whether user can cancel
            parent: Parent widget (defaults to main window)

        Returns:
            QProgressDialog instance for further control
        """
        parent = parent or self.main_window

        self.modal_dialog = QProgressDialog(message, "Cancel" if cancelable else None, 0, maximum, parent)
        self.modal_dialog.setWindowTitle(title)
        self.modal_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.modal_dialog.setAutoClose(True)
        self.modal_dialog.setAutoReset(True)
        self.modal_dialog.setMinimumWidth(350)
        self.modal_dialog.setMinimumHeight(100)

        # Style the dialog
        self.modal_dialog.setStyleSheet("""
            QProgressDialog {
                background-color: #3d3d3d;
            }
            QLabel {
                color: white;
                font-size: 12px;
            }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                background-color: #2d2d2d;
                text-align: center;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)

        # Force the dialog to show immediately (bypass minimumDuration timer)
        self.modal_dialog.setMinimumDuration(0)
        self.modal_dialog.setValue(0)
        self.modal_dialog.show()
        self.modal_dialog.raise_()  # Bring to front
        self.modal_dialog.activateWindow()  # Ensure it's the active window

        # Multiple event processing to ensure dialog is fully rendered
        QApplication.processEvents()
        QApplication.processEvents()
        QApplication.processEvents()

        return self.modal_dialog

    def update_modal(self, value: int = None, message: str = None):
        """Update modal progress dialog.

        Args:
            value: Current value
            message: Optional new message
        """
        if self.modal_dialog:
            if message:
                self.modal_dialog.setLabelText(message)
            if value is not None:
                self.modal_dialog.setValue(value)
            QApplication.processEvents()

    def finish_modal(self):
        """Close modal progress dialog."""
        if self.modal_dialog:
            self.modal_dialog.close()
            self.modal_dialog = None

    def is_modal_canceled(self) -> bool:
        """Check if user canceled the modal dialog."""
        if self.modal_dialog:
            return self.modal_dialog.wasCanceled()
        return False


# Global progress manager instance (set by MainWindow)
_progress_manager: ProgressManager = None


def get_progress_manager() -> ProgressManager:
    """Get the global progress manager instance."""
    return _progress_manager


def set_progress_manager(manager: ProgressManager):
    """Set the global progress manager instance."""
    global _progress_manager
    _progress_manager = manager
