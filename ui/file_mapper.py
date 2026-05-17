# ui/file_mapper.py

import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QComboBox, QLineEdit, QFormLayout, QHBoxLayout, QMessageBox
)

class FileMapperScreen(QWidget):
    def __init__(self, on_mapping_complete_callback):
        super().__init__()
        self.on_mapping_complete = on_mapping_complete_callback
        self.csv_df = None
        self.file_path = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Step 1: Load CSV
        self.layout.addWidget(QLabel("Step 1: Load your CSV file"))
        self.load_button = QPushButton("Browse CSV File")
        self.load_button.clicked.connect(self.select_csv_file)
        self.layout.addWidget(self.load_button)

        # Table preview
        self.table_preview = QTableWidget()
        self.layout.addWidget(self.table_preview)

        # Step 2: Mapping
        self.layout.addWidget(QLabel("Step 2: Map columns"))

        self.mapping_form = QFormLayout()
        self.device_name_input = QLineEdit()
        self.description_input = QLineEdit()
        self.timestamp_selector = QComboBox()

        self.mapping_form.addRow("Device Name:", self.device_name_input)
        self.mapping_form.addRow("Description:", self.description_input)
        self.mapping_form.addRow("Timestamp Column:", self.timestamp_selector)

        self.layout.addLayout(self.mapping_form)

        # Parameter mappings (up to 10)
        self.param_mappings = []
        self.param_layout = QVBoxLayout()
        self.layout.addWidget(QLabel("Map up to 10 parameters:"))
        for i in range(10):
            hbox = QHBoxLayout()
            col_selector = QComboBox()
            unit_input = QLineEdit()
            col_selector.setPlaceholderText("Select column")
            unit_input.setPlaceholderText("Unit (optional)")
            hbox.addWidget(col_selector)
            hbox.addWidget(unit_input)
            self.param_layout.addLayout(hbox)
            self.param_mappings.append((col_selector, unit_input))
        self.layout.addLayout(self.param_layout)

        # Start plotting
        self.start_button = QPushButton("Start Plotting")
        self.start_button.clicked.connect(self.handle_mapping_complete)
        self.layout.addWidget(self.start_button)

    def select_csv_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV files (*.csv)")
        if file_path:
            self.file_path = file_path
            self.load_button.setText(file_path)

            try:
                df = pd.read_csv(file_path)
                self.csv_df = df
                self.show_table_preview(df)
                self.populate_column_selectors(df.columns)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load CSV: {str(e)}")

    def show_table_preview(self, df):
        preview = df.head(10)
        self.table_preview.setRowCount(len(preview))
        self.table_preview.setColumnCount(len(preview.columns))
        self.table_preview.setHorizontalHeaderLabels(preview.columns)

        for i in range(len(preview)):
            for j in range(len(preview.columns)):
                item = QTableWidgetItem(str(preview.iat[i, j]))
                self.table_preview.setItem(i, j, item)

    def populate_column_selectors(self, columns):
        self.timestamp_selector.clear()
        self.timestamp_selector.addItems(columns)
        for col_selector, _ in self.param_mappings:
            col_selector.clear()
            col_selector.addItems([""] + list(columns))

    def handle_mapping_complete(self):
        if not self.file_path:
            QMessageBox.warning(self, "Missing File", "Please load a CSV file first.")
            return

        mapped_params = []
        for col_selector, unit_input in self.param_mappings:
            column = col_selector.currentText()
            unit = unit_input.text()
            if column:
                mapped_params.append({"column": column, "unit": unit})

        if not mapped_params:
            QMessageBox.warning(self, "No Parameters", "Please map at least one parameter column.")
            return

        mapped_data = {
            "file_path": self.file_path,
            "device_name": self.device_name_input.text(),
            "description": self.description_input.text(),
            "timestamp_column": self.timestamp_selector.currentText(),
            "parameters": mapped_params
        }

        self.on_mapping_complete(mapped_data)
