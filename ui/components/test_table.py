from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

class TestTable(QWidget):
    def __init__(self, data, headers, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(data))
        self.table.setSortingEnabled(True)

        for row, item in enumerate(data):
            for col, value in enumerate(item):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

        self.layout.addWidget(self.table)
        self.setLayout(self.layout)
        self.table.itemSelectionChanged.connect(self._selection_changed)

    def update_data(self, data):
        if not data or len(data) == 0:
            self.table.setRowCount(0)
            return
        if len(data[0]) != self.table.columnCount():
            raise ValueError(f"Data columns ({len(data[0])}) do not match table columns ({self.table.columnCount()})")
        current_row = self.table.currentRow() if self.table.rowCount() > 0 else -1
        self.table.setRowCount(len(data))
        for row, item in enumerate(data):
            for col, value in enumerate(item):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))
        if current_row >= 0 and current_row < len(data):
            self.table.setCurrentCell(current_row, 0)

    def _selection_changed(self):
        pass

    def selected_items(self):
        """Return a list of selected items."""
        selected = []
        for item in self.table.selectedItems():
            selected.append(item.text())
        return selected
