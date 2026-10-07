# Changelog

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
