# Changelog

## 1.0.4

### Changed
- Priority removed from the editor and Settings: SillyTavern does not use it. A `priority` value already in a file is kept unchanged.
- Add clears the search, so the new entry is visible in the list.

### Fixed
- Case Sensitive had no effect in SillyTavern: it was saved only as `case_sensitive`, while SillyTavern reads `caseSensitive`. Now both are written. An entry left at SillyTavern's default (`caseSensitive: null`, use the global setting) stays so until you change the checkbox.
- A file with `NaN` or `Infinity` (not valid JSON; SillyTavern cannot read it) opened and was saved back unchanged. Now it is refused with a message.

## 1.0.3

### Added
- Drop a lorebook file anywhere on the window, including a text field, to open it. It works like Open: you are asked to save unsaved changes first; if several files are dropped, the first `.json` is opened; a broken file shows an error and the current lorebook stays open. Dropped plain text is still inserted as before.

### Fixed
- The program could crash (Segmentation fault) after the window was closed. Data was already saved; the crash happened on exit.
- A file dropped onto the Content field inserted its path (`file:///...`) into the entry text.
- A character card, or another JSON file without `entries`, opened as an empty lorebook. Now it is refused with a message, and the current lorebook stays open (Open and drag and drop).

## 1.0.2

### Added
- `LorebookStudio.pyw`: double-click to start without a console window (Windows). Errors are shown in a message box and written to `error.log`.

### Changed
- Author name in the window title and in the license corrected to Egoxode.

### Fixed
- Data change on save: saving the file, or editing any field of an entry, rewrote the whole entry from the editor fields. Windows line endings (`\r\n`) and no-break spaces in the content were replaced, and numbers outside the field range were clamped (for example `order` 150000 became 99999). Now only the fields you change are written; the others keep the exact values from the file.

## 1.0.1

### Added
- All four SillyTavern `Selective Logic` modes: AND ANY, NOT ALL, NOT ANY, AND ALL (editor and Settings).
- Delete asks for confirmation.
- A cloned entry is placed right after the original instead of at the end of the list.
- Entries are renumbered (`uid`, `id`, dictionary keys, `displayIndex` if present) to match the list order on open, save, delete and reorder.

### Fixed
- Data loss: keys that contain a comma (for example regex keys) were split in two after any edit of the entry. Keys are now rewritten only if you change the keyword field.
- Data loss: `Selective Logic` values 2 and 3 were turned into `-1`. Values outside 0-3 are now kept unchanged until you pick a mode.
- Data loss: large values (for example `order` above 999) were silently clamped on the first edit. Field ranges are wider now.
- Files with a UTF-8 BOM could not be opened.
- `null` or invalid values in a file (for example `"probability": null`) crashed the editor. Defaults are used instead; non-object items inside `entries` are dropped.
- A failed open (broken JSON) left the current lorebook half-replaced. The current lorebook is now untouched on error.
- A failed save (file in use, no permission) was silent. An error message is shown now. Saved files keep normal permissions (previously `0600`), and `.json` is added if the extension is missing.
- Drag and drop rebuilt the list inside Qt's drop handler, which could crash. The rebuild is now deferred.
- `Enabled` and `disable` could disagree, so an entry switched off in the editor stayed active in SillyTavern. They are kept in sync now (`disable = not enabled`), also on import.
- `order` and `insertion_order` could disagree for entries that had only one of them.
- `extensions.useProbability` was always forced to `true`.
- Search matched UI text such as "chars", "tokens" and "keywords", so those words matched every entry.
- The search filter was dropped whenever the list was refreshed (add, clone, delete, move).
- Cancelling the save dialog, or pressing Save without changes, marked the lorebook as modified.
- Lorebook statistics lagged one edit behind while typing.
- The editor kept the data of a previous entry after the last entry was deleted or an empty lorebook was opened.
- The lorebook name field was empty on start although the lorebook was called "Lorebook".
- The second line of the selected list item was cut off.
- Pasting formatted text into Content is now converted to plain text.

## 1.0

- First public version.
