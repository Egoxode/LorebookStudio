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

## Usage notes

### File format

- The program saves `entries` as an object with string keys: `"1"`, `"2"`, `"3"`.
- If you open an older lorebook where `entries` is a list, it is converted to this object format.
- This is the normal format for SillyTavern.
- Some websites may change the file after upload and download. That is not controlled by this program.

### Name and comment

- `name` and `comment` are always kept the same.
- The program uses `name` first. If `name` is empty, it uses `comment`.
- This is required because some editors show `name` and others show `comment`.

### Entry order

- The order in the left list is the order written into the saved JSON.
- Moving entries also updates dictionary keys, `uid`, and `id`.
- `Insertion Order` is not changed by moving entries. You set it yourself.
- `order` and `insertion_order` always come from the Insertion Order field.

### Import and new entries

- On import, existing values in the file are not overwritten.
- Settings values are applied only to missing fields.
- A new entry (`+`) uses the current Settings values.

### Search and preview

- Search looks through name, keywords, secondary keywords, and content.
- Markdown Preview follows normal Markdown rules: a single line break does not start a new paragraph. Use a blank line for a new paragraph.

### Other fields

- Token count is an estimate: characters / 4. It is not a model tokenizer.
- `Enabled` turns the entry on.
- `Disable` is a compatibility field for some editors. Leave it off unless you need it.
- `addMemo` is always written as `true`. It does not control activation.

### Settings file

- After you save Settings, the program creates `settings.json` next to the app.
- Do not commit `settings.json` to git. It is a local file.

### Compatibility

- The program is made for SillyTavern and Chub lorebook JSON files.
- If a website returns a different file after download, that change comes from the website.

## License

MIT. You may freely use and modify this program.
