from datetime import datetime
import os
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu-rasterization"
import sys  # ✅ NEW
import json  # ✅ NEW
from pathlib import Path  # ✅ NEW
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QComboBox, QLineEdit, QDialog, QDialogButtonBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QCheckBox, QScrollArea, QSizePolicy, QColorDialog, QSpacerItem, QGridLayout, QGraphicsOpacityEffect, QMessageBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QTimer, QObject, Slot
from PySide6.QtWebChannel import QWebChannel
import base64


class JSBridge(QObject):
    def __init__(self, parent=None):
        super().__init__()
        self.parent = parent  # <- so we can read param_selector

    @Slot(str)
    def saveImage(self, base64Image):
        # Decide metric name from the UI
        metric_name = "Graph"
        try:
            if self.parent:
                if getattr(self.parent, "combine_graph_mode", False):
                    # Combined view naming
                    n = len(getattr(self.parent, "selected_metrics", []) or [])
                    metric_name = f"Combined_{n}" if n > 1 else "Combined"
                else:
                    # Single metric from the dropdown
                    if self.parent.param_selector and self.parent.param_selector.count() > 0:
                        current = self.parent.param_selector.currentText().strip()
                        if current:
                            metric_name = current
                    # last fallback: first selected metric if dropdown somehow empty
                    if metric_name == "Graph" and getattr(self.parent, "selected_metrics", []):
                        metric_name = self.parent.selected_metrics[0]
        except Exception:
            pass

        # Sanitize for filesystem
        safe_metric = (
            metric_name.replace(" ", "_")
                       .replace("/", "-").replace("\\", "-")
                       .replace(":", "-").replace("*", "-")
                       .replace("?", "-").replace('"', "")
                       .replace("<", "-").replace(">", "-").replace("|", "-")
        )

        default_filename = f"FG_{safe_metric}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
        filename, _ = QFileDialog.getSaveFileName(
            None, "Save Graph As", default_filename, "PNG Files (*.png)"
        )
        if not filename:
            return

        # Decode & write
        base64_data = base64Image.split(',', 1)[1] if ',' in base64Image else base64Image
        image_bytes = base64.b64decode(base64_data)
        try:
            with open(filename, "wb") as f:
                f.write(image_bytes)
            QMessageBox.information(None, "Saved", f"Plot saved to:\n{filename}")
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save image:\n{str(e)}")



class PlotWindow(QWidget):
    def __init__(self, theme_manager):
        super().__init__()
        self.theme_manager = theme_manager
        self.file_path = None
        self.timestamp_col = None
        self.metric_units = {}
        self.metric_colors = {}
        self.selected_metrics = []
        self.metric_data = pd.DataFrame(columns=['timestamp'])
        self.last_timestamp = None
        self.combine_graph_mode = False  # ✅ NEW

        # ✅ NEW: settings defaults & load from config
        self.settings = {
            "poll_interval_sec": 3,
            "preview_points": 100,
            "show_titles": True
        }
        self.config_file = self._get_config_path()
        self._load_settings()

        self.init_ui()

    # ✅ NEW: resolve config path next to EXE (or next to script in dev)
    def _get_config_path(self) -> str:
        try:
            if getattr(sys, 'frozen', False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).parent
            return str(base_dir / "fgcsv_config.json")
        except Exception:
            # Fallback to cwd
            return str(Path.cwd() / "fgcsv_config.json")

    # ✅ NEW: load settings json if present
    def _load_settings(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # keep only known keys, apply sane fallbacks
                self.settings["poll_interval_sec"] = int(data.get("poll_interval_sec", 3))
                self.settings["preview_points"]   = int(data.get("preview_points", 100))
                self.settings["show_titles"]      = bool(data.get("show_titles", True))
        except Exception as e:
            # Non-fatal: stick to defaults
            print(f"[Settings] Failed to load config: {e}")

    # ✅ NEW: save settings json
    def _save_settings(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
            self.log("Info", "Settings saved.")
        except Exception as e:
            self.log("Error", f"Failed to save settings: {e}")

    def init_ui(self):
        layout = QVBoxLayout(self)

        # --- Top banner container (keeps your existing buttons) ---
        topbar_widget = QWidget()
        topbar_widget.setObjectName("TopBar")
        topbar_layout = QHBoxLayout(topbar_widget)
        topbar_widget.setFixedHeight(42)
        topbar_layout.setContentsMargins(8, 4, 8, 4)
        topbar_layout.setSpacing(6)

        # ✅ Settings button (to the LEFT of theme button)
        self.settings_button = QPushButton("⚙️")
        self.settings_button.setToolTip("Open Preferences")
        self.settings_button.setFixedSize(24, 24)
        self.settings_button.clicked.connect(self.open_settings_dialog)

        self.theme_button = QPushButton("🌙")
        #self.theme_button.setFixedSize(24, 24)
        self.theme_button.clicked.connect(self.theme_manager.toggle_theme)

        self.about_button = QPushButton("?")
        self.about_button.setFixedSize(24, 24)
        self.about_button.setToolTip("About FlowGraph")
        self.about_button.clicked.connect(self.show_about_dialog)

        topbar_layout.addStretch()
        topbar_layout.addWidget(self.settings_button)
        topbar_layout.addWidget(self.theme_button)
        topbar_layout.addWidget(self.about_button)

        # Style the banner + buttons
        topbar_widget.setStyleSheet("""
            #TopBar {
                background: qlineargradient(
                    spread:pad,
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0d1b3d,   /* deep navy left */
                    stop:1 #060f26    /* slightly lighter navy right */
                );
            }
            #TopBar QPushButton {
            background: transparent;
            color: #ffffff;
            border: none;
            padding: 2px 4px;
            }
            #TopBar QPushButton:hover {
            background: rgba(255,255,255,0.08);
            border-radius: 4px;
            }
            #TopBar QPushButton:pressed {
            background: rgba(255,255,255,0.16);
            }

        """)

        layout.addWidget(topbar_widget)

        # continue as before
        input_preview_layout = QHBoxLayout()

        self.input_panel = QWidget()
        input_layout = QVBoxLayout()
        self.input_panel.setLayout(input_layout)
        input_layout.addWidget(QLabel("📁 Input"))
        self.file_button = QPushButton("Select CSV")
        self.file_button.clicked.connect(self.select_csv)
        input_layout.addWidget(self.file_button)
        self.timestamp_label = QLabel("⏳ Timestamp Column: [Not Set]")
        input_layout.addWidget(self.timestamp_label)
        input_layout.addStretch()
        input_preview_layout.addWidget(self.input_panel, 1)

        self.preview_panel = QWidget()
        preview_layout = QVBoxLayout()
        self.preview_panel.setLayout(preview_layout)
        preview_label_row = QHBoxLayout()
        self.preview_label = QLabel("🔍 File Preview")
        self.preview_filename_label = QLabel("")
        self.preview_filename_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        preview_label_row.addWidget(self.preview_label)
        preview_label_row.addStretch()
        preview_label_row.addWidget(self.preview_filename_label)
        preview_layout.addLayout(preview_label_row)
        self.preview_table = QTableWidget()
        preview_layout.addWidget(self.preview_table)
        input_preview_layout.addWidget(self.preview_panel, 3)

        layout.addLayout(input_preview_layout)

        config_graph_layout = QHBoxLayout()

        self.config_panel = QWidget()
        config_layout = QVBoxLayout(self.config_panel)
        config_layout.addWidget(QLabel("🛠️ Configurator"))
        config_layout.addSpacing(5)
        self.device_input = QLineEdit()
        self.device_input.setPlaceholderText("Device Name")
        self.device_input.setToolTip("Enter to use in graph title")
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Description")
        config_layout.addWidget(self.device_input)
        config_layout.addWidget(self.description_input)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # ✅ Enable horizontal scroll

        self.metric_container = QWidget()
        self.metric_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        scroll.setMinimumHeight(415)
        self.metric_layout = QVBoxLayout()
        self.metric_layout.setAlignment(Qt.AlignTop)
        self.metric_layout.setSpacing(10)
        self.metric_container.setLayout(self.metric_layout)

        self.metric_placeholder = QLabel("Metrics will appear here after a CSV file is loaded.")
        self.metric_placeholder.setStyleSheet("color: gray; font-style: italic;")
        self.metric_placeholder.setAlignment(Qt.AlignCenter)
        self.metric_layout.addWidget(self.metric_placeholder)

        scroll.setWidget(self.metric_container)
        config_layout.addWidget(scroll)
        config_layout.addStretch()
        self.config_panel.setLayout(config_layout)
        config_graph_layout.addWidget(self.config_panel, 1)

        self.graph_panel = QWidget()
        graph_layout = QVBoxLayout(self.graph_panel)

        metric_group = QHBoxLayout()

        control_row = QHBoxLayout()
        self.combine_button = QPushButton("📊")
        self.combine_button.setToolTip("Toggle combined graph view")
        self.combine_button.setCheckable(True)
        self.combine_button.clicked.connect(self.toggle_combine_mode)

        self.param_selector = QComboBox()
        self.param_selector.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.param_selector.setMinimumContentsLength(15)
        self.param_selector.view().setMinimumWidth(100)
        self.param_selector.setToolTip("Change metric")
        self.param_selector.currentIndexChanged.connect(self.update_selected_plot)

        metric_group.addWidget(self.combine_button)
        metric_group.addWidget(self.param_selector)

        # Spacer to push metric_group right
        control_row.addStretch()
        control_row.addLayout(metric_group)

        # Rest of the controls (⏱, ▶️, ⏹️)
        control_row.addSpacing(5)
        poll_icon = QLabel("⏱")
        self.poll_input = QLineEdit(str(self.settings.get("poll_interval_sec", 3)))  # ✅ default from settings
        self.poll_input.setFixedWidth(35)
        self.poll_input.setToolTip("Graph polling interval")
        self.poll_input.editingFinished.connect(self._persist_poll_from_main)

        self.start_button = QPushButton("▶️ Start")
        self.stop_button = QPushButton("⏹️ Stop")
        self.start_button.clicked.connect(self.start_plotting)
        self.stop_button.clicked.connect(self.stop_plotting)
        self.stop_button.setEnabled(False)

        control_row.addWidget(poll_icon)
        control_row.addWidget(self.poll_input)
        control_row.addWidget(QLabel("s"))
        control_row.addSpacing(5)
        control_row.addWidget(self.start_button)
        control_row.addWidget(self.stop_button)
        graph_layout.addLayout(control_row)

        self.plot_view = QWebEngineView()
        self.plot_view.setFixedHeight(463)
        graph_layout.addWidget(self.plot_view)
        self.graph_panel.setLayout(graph_layout)
        config_graph_layout.addWidget(self.graph_panel, 3)

        layout.addLayout(config_graph_layout)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(180)

        console_wrapper = QWidget()
        console_layout = QVBoxLayout(console_wrapper)
        console_layout.setContentsMargins(7, 0, 7, 0)
        console_label = QLabel("🖥️ Console")
        console_layout.addWidget(console_label)
        console_layout.addWidget(self.log_view)
        layout.addWidget(console_wrapper)

        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_csv_for_new_data)
        self.plot_view.setHtml(self.initial_html())
        self.web_channel = QWebChannel()
        self.bridge = JSBridge(self)
        self.web_channel.registerObject("bridge", self.bridge)
        self.plot_view.page().setWebChannel(self.web_channel)
        self.render_placeholder_plot()
        #self.log("Info", "----------------------------------------------")
        self.log("Info", "FlowGraph  v1.0.0")
        self.log("Info", "© 2025  After Access Pty Ltd.  All rights reserved.")
        self.log("Info", "-----------------------------------------------")

    def toggle_combine_mode(self):
        self.combine_graph_mode = self.combine_button.isChecked()
        self.update_selected_plot()

    def select_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV File", "", "CSV files (*.csv)")
        if not file_path:
            return
        try:
            df = pd.read_csv(file_path)
            self.csv_df = df
            self.file_path = file_path
            filename = os.path.basename(file_path)
            self.file_button.setText(filename)
            self.preview_filename_label.setText(filename)
            self.show_csv_preview(df)
            ts_col, ok = self.ask_timestamp_column(df.columns)
            if not ok:
                self.log("Error", "Timestamp selection cancelled.")
                return
            self.timestamp_col = ts_col
            self.timestamp_label.setText(f"⏳ Timestamp Column: {ts_col}")
            self.update_metric_checkboxes([col for col in df.columns if col != ts_col])
            self.log("Info", f"Loaded file {file_path} with timestamp column {ts_col}")
        except Exception as e:
            self.log("Error", f"Failed to load CSV: {e}")

    def ask_timestamp_column(self, columns):
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Timestamp Column")
        dialog.setModal(True)
        dialog.setFixedSize(300, 200)
        layout = QVBoxLayout(dialog)
        combo = QComboBox()
        combo.addItems(columns)
        layout.addWidget(combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        result = dialog.exec()
        return combo.currentText(), result == QDialog.Accepted

    def update_metric_checkboxes(self, metrics):

        # ✅ Remove placeholder message if it exists
        if hasattr(self, "metric_placeholder") and self.metric_placeholder:
            self.metric_layout.removeWidget(self.metric_placeholder)
            self.metric_placeholder.deleteLater()
            self.metric_placeholder = None

        for i in reversed(range(self.metric_layout.count())):
            widget = self.metric_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        self.metric_checkboxes = []

        for metric in metrics:
            row = QWidget()
            row_layout = QGridLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setHorizontalSpacing(10)

            # Column 1: Checkbox
            cb = QCheckBox(metric)
            cb.setMinimumWidth(120)  # ~30 characters
            cb.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

            # Column 2: Unit input
            unit_input = QLineEdit()
            unit_input.setPlaceholderText("Unit (optional)")
            unit_input.setFixedWidth(90)  # ~20 characters
            unit_input.setAlignment(Qt.AlignLeft)

            # Column 3: Color picker
            color_button = QPushButton()
            color_button.setFixedSize(16, 16)
            color_button.setStyleSheet("background-color: #1F77B4; border: 1px solid #666;")

            # Create a unique opacity effect per button
            opacity_effect = QGraphicsOpacityEffect()
            opacity_effect.setOpacity(0.0)  # Start hidden
            color_button.setGraphicsEffect(opacity_effect)
            color_button.setEnabled(False)

            # Set up color dialog per button
            def make_color_picker(btn, m):
                def open_color_picker():
                    color = QColorDialog.getColor()
                    if color.isValid():
                        btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #666;")
                        self.metric_colors[m] = color.name()
                return open_color_picker

            color_button.clicked.connect(make_color_picker(color_button, metric))

            # Set up toggle visibility per button
            def make_toggle(opacity_eff, btn):
                def toggle(checked):
                    opacity_eff.setOpacity(1.0 if checked else 0.0)
                    btn.setEnabled(checked)
                return toggle

            cb.toggled.connect(make_toggle(opacity_effect, color_button))
            cb.toggled.connect(lambda checked, m=metric: self.preview_selected_metrics())

            # Add widgets to layout
            row_layout.addWidget(cb, 0, 0, alignment=Qt.AlignLeft)
            row_layout.addWidget(unit_input, 0, 1, alignment=Qt.AlignLeft)
            row_layout.addWidget(color_button, 0, 2, alignment=Qt.AlignCenter)

            self.metric_layout.addWidget(row)
            self.metric_checkboxes.append((cb, unit_input))

    def show_csv_preview(self, df):
        preview = df.head(10)
        self.preview_table.setRowCount(len(preview))
        self.preview_table.setColumnCount(len(preview.columns))
        self.preview_table.setHorizontalHeaderLabels(preview.columns)
        for i in range(len(preview)):
            for j in range(len(preview.columns)):
                item = QTableWidgetItem(str(preview.iat[i, j]))
                self.preview_table.setItem(i, j, item)

    def start_plotting(self):
        if not self.timestamp_col:
            self.log("Error", "Timestamp column not set.")
            return
        selected = []
        self.metric_units.clear()
        for cb, unit_input in self.metric_checkboxes:
            if cb.isChecked():
                selected.append(cb.text())
                self.metric_units[cb.text()] = unit_input.text().strip()
        if not selected:
            self.log("Error", "No metrics selected.")
            return
        try:
            interval_sec = int(self.poll_input.text())
            if interval_sec <= 0:
                raise ValueError("Interval must be greater than 0")
            interval = interval_sec * 1000
        except Exception:
            self.log("Error", "Invalid polling interval. Must be a number greater than 0.")
            return
       
        if self.settings.get("poll_interval_sec") != interval_sec:
            self.settings["poll_interval_sec"] = interval_sec
            self._save_settings() 
        
        self.poll_timer.setInterval(interval)
        self.selected_metrics = selected
        self.metric_data = pd.DataFrame(columns=['timestamp'] + selected)
        self.param_selector.clear()
        self.param_selector.addItems(self.selected_metrics)
        if self.selected_metrics:
            self.param_selector.setCurrentIndex(0)
        self.poll_timer.start()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.disable_config_inputs(True)
        self.last_timestamp = None
        self.log("Info", "Polling started.")

    def stop_plotting(self):
        self.poll_timer.stop()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.disable_config_inputs(False)
        self.log("Info", "Polling stopped.")

    def disable_config_inputs(self, disable):
        self.file_button.setDisabled(disable)
        self.device_input.setDisabled(disable)
        self.description_input.setDisabled(disable)
        for cb, unit_input in self.metric_checkboxes:
            cb.setDisabled(disable)
            unit_input.setDisabled(disable)
        self.param_selector.setDisabled(False)
        self.poll_input.setDisabled(disable)
        self.settings_button.setDisabled(disable)

    def poll_csv_for_new_data(self):
        if not os.path.exists(self.file_path):
            self.log("Error", "File missing.")
            return
        try:
            df = pd.read_csv(self.file_path)
            df[self.timestamp_col] = pd.to_datetime(df[self.timestamp_col], errors='coerce')
            df = df.dropna(subset=[self.timestamp_col])
            df = df.sort_values(by=self.timestamp_col)
            latest = df.iloc[-1]
            timestamp = latest[self.timestamp_col]
            if self.last_timestamp is not None and timestamp <= self.last_timestamp:
                return
            self.last_timestamp = timestamp

            new_row = {'timestamp': timestamp}
            for metric in self.selected_metrics:
                new_row[metric] = latest.get(metric, None)
            self.metric_data = pd.concat([self.metric_data, pd.DataFrame([new_row])], ignore_index=True)

            self.update_selected_plot()  # ✅ Updated logic

            log_line = f"{timestamp} | " + ', '.join(
                f"{metric} = {latest[metric]}" for metric in self.selected_metrics if pd.notna(latest[metric])
            )
            self.log("Debug", log_line)

        except Exception as e:
            self.log("Error", f"Polling error: {e}")

    def refresh_plot_with_data(self, x_vals, y_vals, title, unit):
        current_metric = self.param_selector.currentText()
        color = self.metric_colors.get(current_metric, "#1F77B4")  # fallback to default

        # ✅ Title toggle via settings
        if not self.settings.get("show_titles", True):
            title = ""

        x_array = ','.join([f'"{x}"' for x in x_vals])
        y_array = ','.join(map(str, y_vals))

        js = f"""
        if (typeof Plotly !== 'undefined' && chartReady) {{
            Plotly.newPlot('chart', [{{
                x: [{x_array}],
                y: [{y_array}],
                mode: 'lines+markers',
                name: '{current_metric}',
                line: {{ color: '{color}' }}
            }}], {{
                title: '{title}',
                paper_bgcolor: '#111',
                plot_bgcolor: '#111',
                font: {{ family: 'Roboto, sans-serif', size: 12, color: '#ddd' }},
                xaxis: {{ title: '', type: 'date' }},
                yaxis: {{ title: '{unit}' }}
            }}, {self._plotly_config_js()});
        }}
        """
        self.plot_view.page().runJavaScript(js)

    def update_selected_plot(self):
        if self.metric_data.empty:
            return
        if self.combine_graph_mode:
            traces = []
            for metric in self.selected_metrics:
                subset = self.metric_data[['timestamp', metric]].dropna()
                x_vals = subset['timestamp'].tolist()
                y_vals = subset[metric].tolist()
                color = self.metric_colors.get(metric, "#1F77B4")
                unit = self.metric_units.get(metric, "")
                label = f"{metric} ({unit})" if unit else metric
                traces.append({
                    "x": x_vals,
                    "y": y_vals,
                    "name": metric,
                    "color": self.metric_colors.get(metric, "#1F77B4"),
                    "unit": self.metric_units.get(metric, "").strip()
                })
            self.render_combined_plot(traces)
        else:
            current_metric = self.param_selector.currentText()
            subset = self.metric_data[['timestamp', current_metric]].dropna()
            x_vals = subset['timestamp'].tolist()
            y_vals = subset[current_metric].tolist()
            unit = self.metric_units.get(current_metric, "Value")
            device = self.device_input.text().strip()
            title = f"{device} | {current_metric}" if device else current_metric
            self.refresh_plot_with_data(x_vals, y_vals, title, unit)

    def render_combined_plot(self, traces):
        js_traces = []
        for trace in traces:
            unit = trace.get("unit", "").strip()
            label = f"{trace['name']} ({unit})" if unit else trace['name']
            x_array = ','.join([f'"{x}"' for x in trace["x"]])
            y_array = ','.join(map(str, trace["y"]))
            js_trace = f""" {{
                x: [{x_array}],
                y: [{y_array}],
                mode: 'lines+markers',
                name: '{label}',
                line: {{ color: '{trace["color"]}' }}
            }} """
            js_traces.append(js_trace)

        device_label = self.device_input.text().strip()
        # ✅ Title toggle via settings
        chart_title = f"{device_label + ' | ' if device_label else ''}Combined Metrics" if self.settings.get("show_titles", True) else ""

        js_code = f"""
        if (typeof Plotly !== 'undefined' && chartReady) {{
            Plotly.newPlot('chart', [{','.join(js_traces)}], {{
                title: '{chart_title}',
                paper_bgcolor: '#111',
                plot_bgcolor: '#111',
                font: {{ family: 'Roboto, sans-serif', size: 12, color: '#ddd' }},
                xaxis: {{ title: '', type: 'date' }},
                yaxis: {{ title: '' }}
            }}, {self._plotly_config_js()});
        }}
        """
        self.plot_view.page().runJavaScript(js_code)

    def render_placeholder_plot(self):
        now = datetime.now()
        self.refresh_plot_with_data([now], [0], "", "")

    def initial_html(self):
        return """
        <html>
        <head>
            <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
            <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
            <style>
                /* Ensure the modebar isn't hidden by hover issues in QWebEngine */
                .modebar { z-index: 9999; }
            </style>
        </head>
        <body style="margin:0; background-color:#111;">
            <div id="chart" style="width:100%; height:100%; position:relative;"></div>
            <script>
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window.bridge = channel.objects.bridge;
                });

                let chartReady = false;

                function drawChart() {
                    Plotly.newPlot('chart', [{
                        x: [], y: [], mode: 'lines+markers', name: 'Live Data'
                    }], {
                        title: '',
                        paper_bgcolor: '#111',
                        plot_bgcolor: '#111',
                        font: { family: 'Roboto, sans-serif', size: 12, color: '#ddd' },
                        xaxis: { title: '', type: 'date' },
                        yaxis: { title: '' }
                    }, {
                        displaylogo: false,
                        displayModeBar: true,      // <-- always show
                        responsive: true,
                        modeBarButtonsToRemove: ['toImage'],
                        modeBarButtonsToAdd: [{
                            name: 'Save Graph to Folder',
                            icon: Plotly.Icons.disk,
                            click: function(gd) {
                                Plotly.toImage(gd, {
                                    format: 'png',
                                    height: 600,
                                    width: 1000
                                }).then(function(dataUrl) {
                                    if (window.bridge && window.bridge.saveImage) {
                                        window.bridge.saveImage(dataUrl);
                                    }
                                });
                            }
                        }]
                    });

                    chartReady = true;
                }

                drawChart();
            </script>
        </body>
        </html>
        """

    def preview_selected_metrics(self):
        if not hasattr(self, 'csv_df') or self.timestamp_col not in self.csv_df.columns:
            return
        try:
            df = self.csv_df.copy()
            df[self.timestamp_col] = pd.to_datetime(df[self.timestamp_col], errors='coerce')
            df = df.dropna(subset=[self.timestamp_col])
            df = df.sort_values(by=self.timestamp_col)

            # Collect currently selected metrics
            selected = [cb.text() for cb, _ in self.metric_checkboxes if cb.isChecked()]
            if not selected:
                return

            # Slice the last N rows from settings
            n = max(1, int(self.settings.get("preview_points", 100)))
            preview_df = df[[self.timestamp_col] + selected].tail(n)
            preview_df = preview_df.rename(columns={self.timestamp_col: "timestamp"})

            # Store into metric_data
            self.metric_data = preview_df.reset_index(drop=True)
            self.selected_metrics = selected

            # Update dropdown if not already populated
            self.param_selector.blockSignals(True)  # Prevent unnecessary triggering
            self.param_selector.clear()
            self.param_selector.addItems(selected)
            self.param_selector.blockSignals(False)

            if selected:
                self.param_selector.setCurrentIndex(0)

            self.log("Info", f"[Preview] Rendering last {n} points for: {', '.join(selected)}")
            QTimer.singleShot(100, self.update_selected_plot)

        except Exception as e:
            self.log("Error", f"Preview error: {e}")

    def log(self, level, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.append(f"[{timestamp}] | [{level}] | {message}")
        print(f"[{level}] {message}")

    def show_about_dialog(self):
        about = QDialog(self)
        about.setWindowTitle("About")
        about.setModal(True)
        about.setFixedSize(300, 200)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        app_title = QLabel("FlowGraph")
        app_title.setStyleSheet("font-size: 12pt;font-weight: bold;")
        app_title.setAlignment(Qt.AlignCenter)

        version = QLabel("Version 1.0.0")
        date = QLabel("Published: 22 August 2025")
        layout.addWidget(QLabel(""))
        author = QLabel("After Access Pty Ltd.")

        for label in (version, date, author):
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 10pt;")

        layout.addWidget(app_title)
        layout.addSpacing(6)
        layout.addWidget(version)
        layout.addWidget(date)
        layout.addWidget(author)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(about.accept)
        layout.addSpacing(10)
        layout.addWidget(buttons)

        about.setLayout(layout)

        about.setStyleSheet("""
            QDialog {
                background-color: palette(window);
                color: palette(window-text);
            }
        """)

        about.exec()

    # ✅ NEW: Settings dialog
    def open_settings_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Preferences")
        dlg.setModal(True)
        dlg.setFixedSize(360, 230)

        layout = QVBoxLayout(dlg)

       #header = QLabel("Tune how AfterCSV behaves")
        #header.setAlignment(Qt.AlignCenter)
        #header.setStyleSheet("font-weight: 600; font-size: 11pt;")
        #layout.addWidget(header)
        #layout.addSpacing(6)

        # Row: Polling interval
        row1 = QHBoxLayout()
        lbl_poll = QLabel("Graph Polling Interval (s)")
        lbl_poll.setToolTip("How often the graph checks the CSV after Start (in seconds).")
        self.input_poll_setting = QLineEdit(str(self.settings.get("poll_interval_sec", 3)))
        self.input_poll_setting.setFixedWidth(60)
        row1.addWidget(lbl_poll)
        row1.addStretch()
        row1.addWidget(self.input_poll_setting)
       # row1.addWidget(QLabel("s"))
        layout.addLayout(row1)

        # Row: Preview points
        row2 = QHBoxLayout()
        lbl_prev = QLabel("Import Preview Data Points")
        lbl_prev.setToolTip("How many recent rows to show when you tick a metric (before polling starts).")
        self.input_preview_points = QLineEdit(str(self.settings.get("preview_points", 100)))
        self.input_preview_points.setFixedWidth(60)
        row2.addWidget(lbl_prev)
        row2.addStretch()
        row2.addWidget(self.input_preview_points)
        layout.addLayout(row2)

        # Row: titles checkbox
        row3 = QHBoxLayout()
        self.chk_titles = QCheckBox("Show Graph Titles")
        self.chk_titles.setChecked(bool(self.settings.get("show_titles", True)))
        self.chk_titles.setToolTip("Toggle main chart title visibility.")
        row3.addWidget(self.chk_titles)
        row3.addStretch()
        layout.addLayout(row3)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        def on_save():
            try:
                poll_val = int(self.input_poll_setting.text().strip())
                if poll_val <= 0:
                    raise ValueError
                prev_val = int(self.input_preview_points.text().strip())
                if prev_val <= 0:
                    raise ValueError
            except Exception:
                QMessageBox.warning(dlg, "Invalid Input",
                                    "Please enter positive whole numbers for interval and preview points.")
                return

            # Apply & persist
            self.settings["poll_interval_sec"] = poll_val
            self.settings["preview_points"] = prev_val
            self.settings["show_titles"] = self.chk_titles.isChecked()
            self._save_settings()

            # Reflect polling interval immediately in the UI textbox (top bar)
            self.poll_input.setText(str(poll_val))

            # If user already previewed metrics, refresh that preview count
            if hasattr(self, "csv_df") and self.timestamp_col:
                self.preview_selected_metrics()

            dlg.accept()
            self.log("Info", "Preferences updated.")

        buttons.accepted.connect(on_save)
        buttons.rejected.connect(dlg.reject)

        dlg.exec()

    def _persist_poll_from_main(self):
        """Persist polling interval typed in the main UI as the new default."""
        try:
            val = int(self.poll_input.text().strip())
            if val <= 0:
                raise ValueError
            if self.settings.get("poll_interval_sec") != val:
                self.settings["poll_interval_sec"] = val
                self._save_settings()
                self.log("Info", f"Default polling interval set to {val}s.")
        except Exception:
            # Keep UI responsive; don't nag here—Start button validation already guards bad input
            pass

    def _plotly_config_js(self):
        # Returns a JS snippet with the Plotly config object (as text) for reuse.
        return """{
            displaylogo: false,
            displayModeBar: true,
            responsive: true,
            modeBarButtonsToRemove: ['toImage'],
            modeBarButtonsToAdd: [{
                name: 'Save Graph to Folder',
                icon: Plotly.Icons.disk,
                click: function(gd) {
                    Plotly.toImage(gd, {
                        format: 'png',
                        height: 600,
                        width: 1000
                    }).then(function(dataUrl) {
                        if (window.bridge && window.bridge.saveImage) {
                            window.bridge.saveImage(dataUrl);
                        }
                    });
                }
            }]
        }"""