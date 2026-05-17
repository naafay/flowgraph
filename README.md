# FlowGraph

**Real-time CSV data visualiser built with Python, PySide6, and Plotly.**

FlowGraph watches a CSV file on disk and plots its columns as live, interactive time-series graphs — no server, no browser, no setup beyond Python. Open a CSV, pick your timestamp column, tick the metrics you care about, and hit Start.

---

## Features

- **Live polling** — reads new rows from any CSV file at a configurable interval (default 3 s)
- **Interactive Plotly charts** — zoom, pan, hover tooltips, and a built-in save-to-PNG button
- **Multi-metric selection** — tick any combination of columns from the configurator panel
- **Combined graph mode** — overlay all selected metrics on a single chart for easy comparison
- **Per-metric colour picker** — assign a distinct colour to each metric
- **Units support** — label the Y-axis with the unit of your choice per metric
- **Preview mode** — instantly renders the last N rows of data when you tick a metric, before polling starts
- **Dark / light theme** — toggle at any time without restarting
- **Persistent preferences** — poll interval, preview point count, and title visibility are saved to `fgcsv_config.json` next to the executable
- **Console log** — timestamped debug output visible inside the app
- **Standalone EXE** — ships as a single-file Windows executable built with PyInstaller (no Python installation required for end users)

---

## Screenshots

> *Coming soon — star the repo to be notified of updates.*

---

## Requirements

| Package | Version |
|---------|---------|
| Python | 3.11+ |
| PySide6 | 6.7+ |
| pandas | 2.0+ |
| watchdog | 4.0+ |
| PyInstaller | 6.0+ *(build only)* |

---

## Quick start (from source)

```bash
# 1. Clone
git clone git@github.com:naafay/flowgraph.git
cd flowgraph

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python main.py
```

---

## Building a standalone executable

The included `FlowGraph.spec` is configured for PyInstaller with a splash screen and no console window.

```bash
pip install pyinstaller
pyinstaller FlowGraph.spec
```

The output EXE will be in `dist/FlowGraph/` or as a single file depending on your spec configuration.

---

## How to use

1. **Select CSV** — click *Select CSV* and browse to your file. A preview of the first 10 rows appears immediately.
2. **Pick the timestamp column** — a dialog prompts you to choose which column holds timestamps (ISO 8601 or any pandas-parseable format works).
3. **Configure metrics** — in the left configurator panel, tick the columns you want to plot. Optionally set a unit label and a custom colour per metric.
4. **Set device name / description** — these appear in the graph title.
5. **Adjust poll interval** — enter the number of seconds between CSV reads in the ⏱ field (or via Preferences ⚙️).
6. **Start** — click ▶️ Start. The graph updates automatically each time new rows appear in the CSV.
7. **Switch metrics** — use the dropdown at the top of the graph panel to switch between metrics without stopping.
8. **Combined view** — click 📊 to overlay all selected metrics on one chart.
9. **Export** — click the floppy-disk icon in the Plotly toolbar to save the current graph as a PNG.
10. **Stop** — click ⏹️ Stop to pause polling. You can change your metric selection and restart without reloading the file.

---

## CSV format

FlowGraph works with any CSV that has:
- A column containing timestamps (any format pandas can parse)
- One or more numeric value columns

Example:

```csv
timestamp,temperature,pressure,humidity
2025-08-25 10:00:00,22.4,1013.2,58.1
2025-08-25 10:00:03,22.6,1013.1,58.3
2025-08-25 10:00:06,22.5,1013.0,58.2
```

---

## Project structure

```
flowgraph/
├── main.py                  # App entry point and splash screen
├── core/
│   └── csv_tailer.py        # File-system watcher (watchdog)
├── ui/
│   ├── plot_window.py       # Main window: metrics, chart, controls
│   ├── file_mapper.py       # CSV column mapping widget
│   └── theme_manager.py     # Dark / light palette management
├── assets/
│   ├── FlowGraph.ico        # App icon
│   └── FlowGraph_splash.png # Splash screen
├── FlowGraph.spec           # PyInstaller build spec
└── requirements.txt
```

---

## License

© 2025 After Access Pty Ltd. All rights reserved.
