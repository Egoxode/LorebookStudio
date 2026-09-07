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

- Python 3.10+
- PySide6
- markdown

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
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

## Notes

- Visual list order and `uid` / `id` are updated when you reorder entries.
- `order` and `insertion_order` come only from the Insertion Order field.
- Token count is an estimate (`characters / 4`).
- `addMemo` is written as `true` automatically.

## License

MIT. You may freely use and modify this program.
