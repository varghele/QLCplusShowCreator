from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtWidgets import QMainWindow, QDialog, QFileDialog, QLineEdit, QFormLayout, QDialogButtonBox


class EffectSelectionDialog(QDialog):
    def __init__(self, effects_dict, parent=None):
        super().__init__(parent)
        self.effects_dict = effects_dict
        self.selected_effect = None
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Select Effect")
        self.setModal(True)
        self.resize(400, 500)

        layout = QtWidgets.QVBoxLayout(self)

        # Add search box
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search effects...")
        layout.addWidget(self.search_box)

        # Create tree widget
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabel("Effects")

        # Add "Clear Effect" as the first item
        self.clear_effect_item = QtWidgets.QTreeWidgetItem(self.tree, ["Clear Effect"])
        self.clear_effect_item.setForeground(0, QtGui.QColor('red'))  # Make it stand out

        self.populate_tree()
        layout.addWidget(self.tree)

        # Add buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Connect search box
        self.search_box.textChanged.connect(self.filter_effects)

    def populate_tree(self):
        for module, effects in self.effects_dict.items():
            module_item = QtWidgets.QTreeWidgetItem(self.tree, [module])
            for effect in effects:
                effect_item = QtWidgets.QTreeWidgetItem(module_item, [effect])

    def filter_effects(self, text):
        text = text.lower()
        # Always show "Clear Effect" option
        self.clear_effect_item.setHidden(False)

        for i in range(1, self.tree.topLevelItemCount()):  # Start from 1 to skip clear effect
            module_item = self.tree.topLevelItem(i)
            module_visible = False

            for j in range(module_item.childCount()):
                effect_item = module_item.child(j)
                effect_visible = text in effect_item.text(0).lower()
                effect_item.setHidden(not effect_visible)
                module_visible = module_visible or effect_visible

            module_item.setHidden(not module_visible)

    def get_selected_effect(self):
        selected_items = self.tree.selectedItems()
        if selected_items:
            item = selected_items[0]
            if item == self.clear_effect_item:
                return "CLEAR"  # Special return value for clearing effect
            elif item.parent():  # If it has a parent, it's an effect
                return f"{item.parent().text(0)}.{item.text(0)}"
        return None

