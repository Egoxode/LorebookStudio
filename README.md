# Lorebook Studio

Desktop editor for SillyTavern / Chub lorebook JSON files.

Version **1.0**

Lorebook Studio was made for convenient editing of lorebooks. You can freely use, copy, and modify this program.

## AI Disclaimer

This project was edited with an AI assistant. Read the code before you rely on it.

## Features

- Open and save lorebooks in dict format (`entries` as an object keyed by UID)
- Convert legacy list-format lorebooks on import
- Create, clone, delete, and reorder entries
- Drag and drop to change entry order
- Manual `Insertion Order` (not overwritten by list position)
- `name` and `comment` stay in sync for editor compatibility
- Search across name, keywords, and content
- Markdown preview
- Default values for new entries and missing import fields
- Dark theme

## Requirements

- Windows, Linux, or macOS
- Python 3.10 or newer
- `pip`

## Install

### 1. Install Python

Install Python 3.10+ from [python.org](https://www.python.org/downloads/).

During setup on Windows, enable:

- **Add python.exe to PATH**

Check that Python works:

```bash
python --version
```

If `python` is not found, try:

```bash
py --version
```

### 2. Download the program

Clone the repository:

```bash
git clone https://github.com/Egoxode/LorebookStudio.git
cd LorebookStudio
```

Or download the ZIP from GitHub and unpack it, then open that folder in a terminal.

### 3. Create a virtual environment (recommended)

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

After activation, your terminal prompt should show `(.venv)`.

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

This installs:

- `PySide6` — interface
- `markdown` — preview

### 5. Run

```bash
python main.py
```

On some systems:

```bash
python3 main.py
```

or:

```bash
py main.py
```

## Keyboard shortcuts

- `Ctrl+S` — Save File
- `Ctrl+O` — Open
- `Ctrl+N` — New lorebook
- `Ctrl+F` — Focus search
- `Ctrl+D` — Clone current entry

## Settings

Open **Settings** in the app to change default values used when:

- creating a new entry (`+`)
- importing a lorebook (only missing fields are filled)

Settings are stored in `settings.json` next to the program. This file is local and is not part of the repository.

## Troubleshooting

**`python` is not recognized**  
Python is not in PATH. Reinstall Python and enable **Add python.exe to PATH**, or use `py` instead of `python`.

**`No module named PySide6`**  
Dependencies were not installed, or you are not inside the virtual environment. Run `pip install -r requirements.txt` again.

**`No module named app`**  
Run `python main.py` from the project root folder, the same folder that contains `main.py` and `app/`.

**Window opens, but spinbox arrows or checkboxes look wrong**  
Make sure the `app/icons/` folder was downloaded: `up.png`, `down.png`, `check.png`.

## Notes

- Visual list order and `uid` / `id` are updated when you reorder entries.
- `order` and `insertion_order` come only from the Insertion Order field.
- Token count is an estimate (`characters / 4`).
- `addMemo` is written as `true` automatically.

## License

MIT. You may freely use and modify this program.
