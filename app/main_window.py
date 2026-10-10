import sys
import copy
import json
import markdown
import shiboken6
from PySide6.QtCore import QTimer, Qt, QEvent
from PySide6.QtGui import QShortcut, QKeySequence
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFormLayout,
    QLineEdit, QListWidget, QListWidgetItem, QPushButton, QTabWidget,
    QSpinBox, QCheckBox, QComboBox, QTextEdit, QLabel, QTextBrowser,
    QFileDialog, QMessageBox, QAbstractItemView
)
from .theme import get_dark_theme
from .storage import load_json, save_json
from .settings import (
    load_settings, save_settings, SettingsDialog, RANGES, SELECTIVE_LOGIC, SELECTIVE_LOGIC_HINT
)


def _to_int(value, default):
    """Безопасное int(): None, строки и мусор из чужих файлов не должны ронять редактор."""
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default


def _to_list(value):
    """Ключевые слова как список строк (допускает список, строку через запятую или мусор)."""
    if isinstance(value, str):
        return [x.strip() for x in value.split(",") if x.strip()]
    if isinstance(value, (list, tuple)):
        return [str(x) for x in value if x is not None and str(x) != ""]
    return []


def _first_list(entry, *names):
    """Первый непустой список среди альтернативных имён поля (key/keys, keysecondary/secondary_keys)."""
    for name in names:
        items = _to_list(entry.get(name))
        if items:
            return items
    return []


def _parse_keys(text, existing):
    """Разобрать строку из поля ввода. Если пользователь не менял список, оставить исходные
    значения как есть (ключи с запятой внутри не должны молча разваливаться на части)."""
    parsed = [x.strip() for x in text.split(",") if x.strip()]
    if [x.strip() for x in ",".join(existing).split(",") if x.strip()] == parsed:
        return list(existing)
    return parsed


def raw_text(edit) -> str:
    """Text of the field exactly as typed. toPlainText() would turn no-break spaces (U+00A0)
    into normal spaces and U+2028 into a line break; the raw text keeps them."""
    return edit.document().toRawText().replace("\u2029", "\n")


def _keep_line_endings(new_text: str, old_text) -> str:
    """Edited text is written in the line-ending style of the original (Windows \\r\\n or \\n)."""
    old = old_text if isinstance(old_text, str) else ""
    if "\n" in old and old.count("\n") == old.count("\r\n"):
        return new_text.replace("\r\n", "\n").replace("\n", "\r\n")
    return new_text


# Editor field -> entry keys it writes (top level, inside "extensions").
# Only fields the user changed are written; the others keep the exact values from the file.
FIELD_KEYS = {
    "name": (("name", "comment"), ()),
    "keys": (("key", "keys"), ()),
    "secondary": (("keysecondary", "secondary_keys"), ()),
    "order": (("insertion_order", "order"), ()),
    "depth": (("depth",), ("depth",)),
    "probability": (("probability",), ("probability",)),
    # SillyTavern читает caseSensitive, формат V2 — case_sensitive: пишем оба.
    "case_sensitive": (("caseSensitive", "case_sensitive"), ()),
    "excludeRecursion": (("excludeRecursion",), ("excludeRecursion",)),
    "selective": (("selective",), ()),
    "constant": (("constant",), ()),
    "enabled": (("enabled", "disable"), ()),
    "selectiveLogic": (("selectiveLogic",), ("selectiveLogic",)),
    "content": (("content",), ()),
}


def _not_lorebook_reason(obj):
    """Почему файл не открывается как lorebook (None — открывать)."""
    if isinstance(obj, list):
        return None  # старый формат: список записей в корне
    if not isinstance(obj, dict):
        return "This file is not a lorebook."
    data = obj.get("data")
    if (str(obj.get("spec", "")).startswith("chara_card")
            or (isinstance(data, dict) and "first_mes" in data)
            or ("first_mes" in obj and "entries" not in obj)):
        return "This file is a character card, not a lorebook."
    if "entries" not in obj:
        return 'This file is not a lorebook: it has no "entries".'
    return None


def _entry_label(position, name, chars, keyword_count):
    return f"{position}. {name or 'Unnamed Entry'}\n{chars} chars | {max(0, chars // 4)} tokens | {keyword_count} keywords"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1600, 900)

        self.data = {"name": "Lorebook", "entries": {}}
        self.ids = []
        self.current_file = None
        self.dirty = False
        self._loading = False
        self._reorder_pending = False
        # Entry shown in the editor: its key, a copy of its values and what the fields showed after loading.
        self._shown_eid = None
        self._shown_entry = None
        self._shown_state = None
        self.app_settings = load_settings()

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        left = QVBoxLayout()
        self.lorebook_name = QLineEdit("Lorebook")
        self.update_title()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search name, keys, content...")
        self.search.textChanged.connect(self.filter_entries)
        self.lorebook_name.textChanged.connect(self.on_lorebook_name_changed)

        self.list = QListWidget()
        self.list.setDragDropMode(QAbstractItemView.InternalMove)
        self.list.setDefaultDropAction(Qt.MoveAction)
        self.list.model().rowsMoved.connect(self.on_rows_moved)
        self.list.currentRowChanged.connect(self.on_row_changed)

        self.btn_new = QPushButton("New")
        self.btn_open = QPushButton("Open")
        self.btn_savefile = QPushButton("Save File")
        self.btn_settings = QPushButton("Settings")
        self.btn_add = QPushButton("+")
        self.btn_saveentry = QPushButton("Save")
        self.btn_up = QPushButton("▲")
        self.btn_down = QPushButton("▼")
        self.btn_clone = QPushButton("Clone")
        self.btn_delete = QPushButton("Delete")

        self.btn_new.clicked.connect(self.new_lorebook)
        self.btn_open.clicked.connect(self.open_file)
        self.btn_savefile.clicked.connect(self.save_file)
        self.btn_settings.clicked.connect(self.open_settings)
        self.btn_add.clicked.connect(self.add_entry)
        self.btn_saveentry.clicked.connect(self.save_entry)
        self.btn_up.clicked.connect(self.move_up)
        self.btn_down.clicked.connect(self.move_down)
        self.btn_clone.clicked.connect(self.clone_entry)
        self.btn_delete.clicked.connect(self.delete_entry)

        left.addWidget(self.btn_new)
        left.addWidget(self.btn_open)
        left.addWidget(self.btn_savefile)
        left.addWidget(self.btn_settings)
        left.addWidget(self.lorebook_name)
        left.addWidget(self.search)
        left.addWidget(self.list)

        tabs = QTabWidget()
        editor = QWidget()
        form = QFormLayout(editor)

        self.name = QLineEdit()
        self.keys = QLineEdit()
        self.secondary = QLineEdit()

        self.insertion_order = QSpinBox()
        self.insertion_order.setRange(*RANGES["insertion_order"])
        self.insertion_order.setSingleStep(1)
        self.insertion_order.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.depth = QSpinBox()
        self.depth.setRange(*RANGES["depth"])
        self.depth.setSingleStep(1)
        self.depth.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.probability = QSpinBox()
        self.probability.setRange(*RANGES["probability"])
        self.probability.setSingleStep(1)
        self.probability.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)

        self.case_sensitive = QCheckBox()
        self.exclude_recursion = QCheckBox("")
        self.selective = QCheckBox()
        self.constant = QCheckBox()
        self.enabled = QCheckBox()

        self.selective_logic = QComboBox()
        self.selective_logic.addItems(SELECTIVE_LOGIC)

        self.content = QTextEdit()
        self.content.setAcceptRichText(False)
        self.counter_label = QLabel("Characters: 0 | Tokens: 0")
        self.lorebook_stats_label = QLabel("Lorebook Statistics: Entries 0 | Characters 0 | Tokens 0")

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_preview)
        self.content.textChanged.connect(lambda: self.preview_timer.start(300))
        self.content.textChanged.connect(self.update_counter)

        for w in [self.name, self.keys, self.secondary]:
            w.textChanged.connect(self.current_save)
        self.content.textChanged.connect(self.current_save)
        for w in [self.case_sensitive, self.exclude_recursion, self.selective, self.constant, self.enabled]:
            w.toggled.connect(self.current_save)
        for w in [self.insertion_order, self.depth, self.probability]:
            w.valueChanged.connect(self.current_save)
        self.selective_logic.currentIndexChanged.connect(self.current_save)

        field_hints = [
            ("Name", self.name, "Display name of this entry. Also saved as comment for other editors."),
            ("Keywords", self.keys, "The keys that activate the content."),
            ("Secondary Keywords", self.secondary, "Additional keys required to activate the content. Ignored if Selective is off."),
            ("Insertion Order", self.insertion_order, "If multiple entries are inserted, lower Insertion Order is inserted higher."),
            ("Case Sensitive", self.case_sensitive, "Whether the keywords are case-sensitive."),
            ("Non-recursable", self.exclude_recursion, "Prevent this entry from being activated by other lorebook entries."),
            ("Selective", self.selective, "Require both keywords and secondary keywords to trigger the entry."),
            ("Selective Logic", self.selective_logic, SELECTIVE_LOGIC_HINT),
            ("Constant", self.constant, "Always trigger this entry (within the token budget)."),
            ("Probability", self.probability, "Percent chance the content is activated when the entry is triggered."),
            ("Depth", self.depth, "How many recent messages to scan for keywords."),
            ("Enabled", self.enabled, "Turns this entry on. If unchecked, the entry will not activate."),
            ("Content", self.content, "The content that gets activated and sent to the AI."),
            ("Statistics", self.counter_label, "Character and token count for this entry."),
            ("Lorebook Statistics", self.lorebook_stats_label, "Totals for the whole lorebook."),
        ]

        for label, widget, hint in field_hints:
            box = QWidget()
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(0, 0, 0, 0)
            box_layout.setSpacing(2)
            box_layout.addWidget(widget)
            hint_label = QLabel(hint)
            hint_label.setWordWrap(True)
            hint_label.setStyleSheet("color: #888; font-size: 11px;")
            box_layout.addWidget(hint_label)
            form.addRow(label, box)
            widget.setToolTip(hint)

        self.preview = QTextBrowser()
        tabs.addTab(editor, "Editor")
        tabs.addTab(self.preview, "Markdown Preview")

        layout.addLayout(left, 1)

        actions = QVBoxLayout()
        actions.setSpacing(4)
        actions.setContentsMargins(0, 0, 0, 0)
        actions.addWidget(self.btn_add)
        actions.addWidget(self.btn_saveentry)
        actions.addWidget(self.btn_up)
        actions.addWidget(self.btn_down)
        actions.addWidget(self.btn_clone)
        actions.addWidget(self.btn_delete)
        actions.addStretch()
        actions_widget = QWidget()
        actions_widget.setFixedWidth(90)
        actions_widget.setLayout(actions)
        layout.addWidget(actions_widget)

        right = QVBoxLayout()
        right.addWidget(tabs)
        layout.addLayout(right, 3)

        self._setup_shortcuts()

        # Файл, брошенный в любое место окна (и на текстовое поле), открывается как через Open,
        # а не вставляется в текст путём.
        self.setAcceptDrops(True)
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)

    def eventFilter(self, obj, event):
        kind = event.type()
        # Только виджеты этого окна (не окно настроек и не окна сообщений).
        if kind in (QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop) \
                and isinstance(obj, QWidget) and obj.window() is self:
            mime = event.mimeData()
            paths = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()] if mime and mime.hasUrls() else []
            if paths:
                if kind == QEvent.Type.Drop:
                    # Первый .json (если его нет — первый файл, и Open покажет ошибку).
                    path = next((x for x in paths if x.lower().endswith(".json")), paths[0])
                    # Открываем после завершения drop: окно с вопросом внутри обработчика
                    # заблокировало бы Проводник, из которого тащат файл.
                    QTimer.singleShot(0, lambda: self.open_dropped(path))
                event.acceptProposedAction()
                return True
        return super().eventFilter(obj, event)

    def open_dropped(self, path):
        if self.confirm_unsaved():
            self.open_path(path)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_file)
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_file)
        QShortcut(QKeySequence("Ctrl+N"), self, self.new_lorebook)
        QShortcut(QKeySequence("Ctrl+F"), self, self.focus_search)
        QShortcut(QKeySequence("Ctrl+D"), self, self.clone_entry)

    def focus_search(self):
        self.search.setFocus()
        self.search.selectAll()

    # ---------- Utility ----------

    def on_lorebook_name_changed(self, t):
        self.data["name"] = t
        if getattr(self, "_loading", False):
            return
        self.dirty = True
        self.update_title()

    def update_title(self):
        lorebook = self.lorebook_name.text().strip() or "Lorebook"
        if self.dirty:
            self.setWindowTitle(f"Lorebook Studio by Egoxode - {lorebook} *")
        else:
            self.setWindowTitle(f"Lorebook Studio by Egoxode - {lorebook}")

    def sync_ids_from_entries(self):
        """Sync self.ids from current entries dict (sorted by numeric key)."""
        entries = self.data.get("entries", {})
        if not isinstance(entries, dict):
            entries = {}
        self.ids = [
            eid for eid, _ in sorted(
                entries.items(),
                key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0
            )
        ]

    def sync_ids_from_list_widget(self):
        """Rebuild self.ids from current visual order in QListWidget (used after drag & drop)."""
        new_ids = []
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item:
                eid = item.data(Qt.UserRole)
                if eid is not None:
                    new_ids.append(str(eid))
        self.ids = new_ids

    def rebuild_entries_dict_order(self):
        """Rebuild self.data['entries'] so keys follow the current visual order in self.ids.
        This ensures the saved JSON has entries in the order the user arranged them."""
        entries = self.data.get("entries", {})
        if not isinstance(entries, dict):
            return

        ordered = {}
        # First add entries in the order of self.ids
        for eid in self.ids:
            if eid in entries:
                ordered[eid] = entries[eid]

        # Then add any remaining entries that weren't in self.ids (safety)
        for eid, e in entries.items():
            if eid not in ordered:
                ordered[eid] = e

        self.data["entries"] = ordered

    # ---------- Core list management ----------

    def refresh(self):
        """Rebuild the QListWidget from self.data['entries'] preserving order in self.ids."""
        self.list.clear()
        self.list.setCurrentRow(-1)

        entries = self.data.get("entries", {})
        if not isinstance(entries, dict):
            entries = {}

        if not self.ids:
            self.sync_ids_from_entries()

        display_order = [eid for eid in self.ids if eid in entries]
        if not display_order:
            display_order = sorted(
                entries.keys(),
                key=lambda x: int(x) if str(x).isdigit() else 0
            )
        self.ids = list(display_order)

        for idx, eid in enumerate(display_order, start=1):
            e = entries.get(eid, {})
            name = e.get("name") or e.get("comment") or ""
            chars = len(str(e.get("content", "")))
            kw_count = len(_first_list(e, "key", "keys"))
            item = QListWidgetItem(_entry_label(idx, name, chars, kw_count))
            item.setData(Qt.UserRole, eid)
            self.list.addItem(item)

        if not display_order:
            self.clear_editor()
        self.filter_entries(self.search.text())
        self.update_lorebook_stats()

    def filter_entries(self, text):
        query = (text or "").strip().lower()
        entries = self.data.get("entries", {})
        if not isinstance(entries, dict):
            entries = {}

        for i in range(self.list.count()):
            item = self.list.item(i)
            if not item:
                continue
            if not query:
                item.setHidden(False)
                continue

            eid = item.data(Qt.UserRole)
            e = entries.get(str(eid), {}) if eid is not None else {}
            if not isinstance(e, dict):
                e = {}

            parts = [
                str(e.get("name", "")),
                str(e.get("comment", "")),
                str(e.get("content", "")),
            ]

            for key_name in ("key", "keys", "keysecondary", "secondary_keys"):
                val = e.get(key_name, "")
                if isinstance(val, list):
                    parts.append(" ".join(str(x) for x in val))
                else:
                    parts.append(str(val or ""))

            haystack = " ".join(parts).lower()
            item.setHidden(query not in haystack)

    def on_row_changed(self, row):
        self.load_entry(row)

    def load_entry(self, row):
        if row < 0 or row >= len(self.ids):
            return

        eid = self.ids[row]
        entries = self.data.get("entries", {})
        if eid not in entries:
            return

        self._loading = True
        try:
            e = entries[eid]
            self.name.setText(str(e.get("name") or e.get("comment") or ""))
            self.keys.setText(",".join(_first_list(e, "key", "keys")))
            self.secondary.setText(",".join(_first_list(e, "secondary_keys", "keysecondary")))

            self.insertion_order.setValue(_to_int(e.get("insertion_order", e.get("order")), 100))
            cs = e.get("caseSensitive")
            self.case_sensitive.setChecked(cs if isinstance(cs, bool) else bool(e.get("case_sensitive", False)))
            self.exclude_recursion.setChecked(bool(e.get("excludeRecursion", False)))
            self.selective.setChecked(bool(e.get("selective", False)))
            # Незнакомое значение (вне 0-3) показываем пустым и не трогаем при сохранении.
            logic = _to_int(e.get("selectiveLogic"), 0)
            self.selective_logic.setCurrentIndex(logic if 0 <= logic < self.selective_logic.count() else -1)
            self.constant.setChecked(bool(e.get("constant", False)))
            self.probability.setValue(_to_int(e.get("probability"), 100))
            self.depth.setValue(_to_int(e.get("depth"), 0))
            self.enabled.setChecked(bool(e.get("enabled", True)) and not e.get("disable", False))
            self.content.setPlainText(str(e.get("content") or ""))
            self._shown_eid = eid
            self._shown_entry = copy.deepcopy(e)
            self._shown_state = self._editor_state()
        finally:
            self._loading = False

        self.update_preview()
        self.update_counter()
        self.update_lorebook_stats()

    def update_preview(self):
        try:
            self.preview.setHtml(markdown.markdown(self.content.toPlainText()))
        except Exception:
            self.preview.setPlainText(self.content.toPlainText())

    def update_counter(self):
        chars = len(raw_text(self.content))
        self.counter_label.setText(f"Characters: {chars} | Tokens: {max(0, chars // 4)}")

    def update_lorebook_stats(self):
        try:
            entries = self.data.get("entries", {})
            if not isinstance(entries, dict):
                entries = {}
            total_chars = 0
            for e in entries.values():
                if isinstance(e, dict):
                    total_chars += len(str(e.get("content", "")))
            total_tokens = max(0, total_chars // 4)
            self.lorebook_stats_label.setText(
                f"Entries: {len(entries)} | Characters: {total_chars} | Tokens: {total_tokens}"
            )
        except Exception as ex:
            print("update_lorebook_stats error:", ex)

    def update_current_item_info(self):
        """Обновить подпись текущего элемента списка по живым значениям редактора."""
        try:
            row = self.list.currentRow()
            item = self.list.item(row)
            if item is None or row >= len(self.ids):
                return
            e = self.data.get("entries", {}).get(self.ids[row], {})
            item.setText(_entry_label(
                row + 1,
                self.name.text(),
                len(raw_text(self.content)),
                len(_first_list(e, "key", "keys")),
            ))
        except Exception as ex:
            print("update_current_item_info error:", ex)

    def clear_editor(self):
        """Сбросить поля редактора к значениям по умолчанию (нет выбранной записи)."""
        s = self.app_settings
        self._shown_eid = self._shown_entry = self._shown_state = None
        self._loading = True
        try:
            self.name.clear()
            self.keys.clear()
            self.secondary.clear()
            self.content.clear()
            self.insertion_order.setValue(_to_int(s.get("insertion_order"), 100))
            self.depth.setValue(_to_int(s.get("depth"), 0))
            self.probability.setValue(_to_int(s.get("probability"), 100))
            self.case_sensitive.setChecked(bool(s.get("case_sensitive", False)))
            self.exclude_recursion.setChecked(bool(s.get("excludeRecursion", False)))
            self.selective.setChecked(bool(s.get("selective", False)))
            self.selective_logic.setCurrentIndex(_to_int(s.get("selectiveLogic"), 0))
            self.constant.setChecked(bool(s.get("constant", False)))
            self.enabled.setChecked(bool(s.get("enabled", True)) and not s.get("disable", False))
        finally:
            self._loading = False
        self.update_preview()
        self.update_counter()

    # ---------- Save current editor state to data ----------

    def _editor_state(self) -> dict:
        """Values of the editor fields, keyed like FIELD_KEYS."""
        return {
            "name": self.name.text(),
            "keys": self.keys.text(),
            "secondary": self.secondary.text(),
            "order": self.insertion_order.value(),
            "depth": self.depth.value(),
            "probability": self.probability.value(),
            "case_sensitive": self.case_sensitive.isChecked(),
            "excludeRecursion": self.exclude_recursion.isChecked(),
            "selective": self.selective.isChecked(),
            "constant": self.constant.isChecked(),
            "enabled": self.enabled.isChecked(),
            "selectiveLogic": self.selective_logic.currentIndex(),
            "content": raw_text(self.content),
        }

    def _write_field(self, e, field, value, original):
        """Write one edited field into the entry (all keys that mirror it)."""
        ext = e.get("extensions")
        if not isinstance(ext, dict):
            ext = e["extensions"] = {}
        if field == "name":
            e["name"] = e["comment"] = value  # редакторы берут либо name, либо comment
        elif field == "keys":
            kw = _parse_keys(value, _first_list(original, "key", "keys"))
            e["key"], e["keys"] = list(kw), list(kw)
        elif field == "secondary":
            sk = _parse_keys(value, _first_list(original, "secondary_keys", "keysecondary"))
            e["keysecondary"], e["secondary_keys"] = list(sk), list(sk)
        elif field == "order":
            e["insertion_order"] = e["order"] = value
        elif field == "enabled":
            # SillyTavern читает `disable`, Chub — `enabled`: держим их согласованными.
            e["enabled"], e["disable"] = value, not value
        elif field == "selectiveLogic":
            if value >= 0:  # -1 = незнакомый режим из чужого файла, не перезаписываем
                e["selectiveLogic"] = ext["selectiveLogic"] = value
        elif field == "content":
            e["content"] = _keep_line_endings(value, original.get("content"))
        else:
            top, in_ext = FIELD_KEYS[field]
            for key in top:
                e[key] = value
            for key in in_ext:
                ext[key] = value

    @staticmethod
    def _restore_field(e, field, original):
        """Put the keys of an unchanged field back exactly as they were in the file."""
        top, in_ext = FIELD_KEYS[field]
        for key in top:
            if key in original:
                e[key] = copy.deepcopy(original[key])
            else:
                e.pop(key, None)
        if in_ext:
            orig_ext = original.get("extensions") if isinstance(original.get("extensions"), dict) else {}
            ext = e.get("extensions")
            if isinstance(ext, dict):
                for key in in_ext:
                    if key in orig_ext:
                        ext[key] = copy.deepcopy(orig_ext[key])
                    else:
                        ext.pop(key, None)

    def _write_editor_to_entry(self, e, eid):
        """Write only the fields the user changed. Unchanged fields keep the exact file values:
        the editor may show them differently (clamped numbers, line endings, no-break spaces)."""
        current = self._editor_state()
        if eid != self._shown_eid or self._shown_state is None:
            # The editor does not show this entry: nothing to compare with, write nothing.
            return
        original, shown = self._shown_entry, self._shown_state
        for field in FIELD_KEYS:
            if current[field] != shown[field]:
                self._write_field(e, field, current[field], original)
            else:
                self._restore_field(e, field, original)

    def current_save(self, *args):
        if getattr(self, "_loading", False):
            return
        r = self.list.currentRow()
        if r < 0 or r >= len(self.ids):
            return
        entries = self.data.setdefault("entries", {})
        eid = self.ids[r]
        if eid not in entries:
            return
        e = entries[eid]

        before = json.dumps(e, sort_keys=True, ensure_ascii=False)
        self._write_editor_to_entry(e, eid)
        if json.dumps(e, sort_keys=True, ensure_ascii=False) == before:
            return  # ничего не изменилось: не помечаем файл как изменённый

        self.update_current_item_info()
        self.update_lorebook_stats()
        self.dirty = True
        self.update_title()

    # ---------- Entry conversion (list -> dict) ----------

    def convert_entries_to_dict(self):
        """Convert legacy list of entries into dict keyed by UID (string keys).
        Non-dict garbage inside `entries` is dropped."""
        entries = self.data.get("entries", {})
        if isinstance(entries, dict):
            self.data["entries"] = {k: v for k, v in entries.items() if isinstance(v, dict)}
            return
        if not isinstance(entries, list):
            self.data["entries"] = {}
            return

        new_entries = {}
        used = set()
        for i, e in enumerate(entries):
            if not isinstance(e, dict):
                continue
            uid = str(_to_int(e.get("uid", e.get("id")), i + 1))
            while uid in used:
                uid = str(int(uid) + 1)
            used.add(uid)

            e = copy.deepcopy(e)
            e["uid"] = int(uid)
            e["id"] = int(uid)
            new_entries[uid] = e

        self.data["entries"] = new_entries

    def normalize_entry(self, key, e):
        """Ensure an entry has all required fields with sane defaults (filled from Settings
        only where missing) and that duplicated fields agree with each other."""
        s = self.app_settings

        # name == comment (разные редакторы показывают разные поля)
        name = e.get("name") or e.get("comment") or f"Entry {key}"
        e["name"] = e["comment"] = str(name)
        e["content"] = str(e.get("content") or "")

        kw = _first_list(e, "key", "keys")
        sk = _first_list(e, "secondary_keys", "keysecondary")
        e["key"], e["keys"] = list(kw), list(kw)
        e["keysecondary"], e["secondary_keys"] = list(sk), list(sk)

        # caseSensitive (SillyTavern) главнее; null/нет — «как в общих настройках ST», не трогаем,
        # но включённую галочку переносим, чтобы ST её видел.
        cs = e.get("caseSensitive")
        if isinstance(cs, bool):
            e["case_sensitive"] = cs
        else:
            e["case_sensitive"] = bool(e.get("case_sensitive", s.get("case_sensitive", False)))
            if e["case_sensitive"]:
                e["caseSensitive"] = True

        for field, default in (("selective", False),
                               ("constant", False), ("excludeRecursion", False),
                               ("useProbability", True), ("addMemo", True)):
            e[field] = bool(e.get(field, s.get(field, default)))

        order = _to_int(e.get("insertion_order", e.get("order")), _to_int(s.get("insertion_order"), 100))
        e["order"] = e["insertion_order"] = order
        for field, setting, default in (("probability", "probability", 100),
                                        ("depth", "depth", 0), ("selectiveLogic", "selectiveLogic", 0)):
            e[field] = _to_int(e.get(field), _to_int(s.get(setting), default))

        # SillyTavern использует `disable`, Chub — `enabled`: запись выключена, если выключено любое из них.
        if "enabled" in e or "disable" in e:
            enabled = bool(e.get("enabled", True)) and not e.get("disable", False)
        else:
            enabled = bool(s.get("enabled", True)) and not s.get("disable", False)
        e["enabled"], e["disable"] = enabled, not enabled

        if not isinstance(e.get("extensions"), dict):
            e["extensions"] = {}
        ext = e["extensions"]
        ext.setdefault("depth", e["depth"])
        ext.setdefault("probability", e["probability"])
        ext.setdefault("useProbability", e["useProbability"])
        ext.setdefault("selectiveLogic", e["selectiveLogic"])
        ext.setdefault("addMemo", e["addMemo"])
        ext.setdefault("excludeRecursion", e["excludeRecursion"])

    def normalize_entries(self):
        entries = self.data.get("entries", {})
        if not isinstance(entries, dict):
            return
        for key, e in entries.items():
            if isinstance(e, dict):
                self.normalize_entry(key, e)

    # ---------- File operations ----------

    def new_lorebook(self):
        """Create a blank lorebook. Ask to save if there are unsaved changes."""
        if self.dirty:
            r = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Save changes before creating a new lorebook?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            if r == QMessageBox.Cancel:
                return
            if r == QMessageBox.Yes:
                self.save_file()
                if self.dirty:
                    return  # user cancelled save dialog

        self.data = {"name": "Lorebook", "entries": {}}
        self.ids = []
        self.current_file = None
        self.dirty = False

        self.list.clear()
        self._loading = True
        try:
            self.lorebook_name.setText("Lorebook")
        finally:
            self._loading = False
        self.clear_editor()
        self.update_title()
        self.update_lorebook_stats()

    def open_settings(self):
        dlg = SettingsDialog(self, self.app_settings)
        if dlg.exec():
            self.app_settings = dlg.values()
            try:
                save_settings(self.app_settings)
            except OSError as e:
                QMessageBox.warning(
                    self, "Settings",
                    f"Settings are applied for this session, but could not be saved:\n{e}"
                )

    def confirm_unsaved(self):
        """Вопрос о несохранённых правках перед открытием другого лорбука. False — отмена."""
        if self.dirty:
            r = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Save changes before opening another lorebook?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            if r == QMessageBox.Cancel:
                return False
            if r == QMessageBox.Yes:
                self.save_file()
                if self.dirty:
                    return False
        return True

    def open_file(self):
        if not self.confirm_unsaved():
            return
        p, _ = QFileDialog.getOpenFileName(self, "Open", "", "JSON (*.json)")
        if p:
            self.open_path(p)

    def open_path(self, p):
        # Всё готовим во временных переменных: при ошибке текущий лорбук остаётся нетронутым.
        previous = self.data
        try:
            loaded = load_json(p)
            reason = _not_lorebook_reason(loaded)
            if reason:
                QMessageBox.critical(self, "Not a lorebook", f"{reason}\n\n{Path(p).name}\n\nThe current lorebook was not changed.")
                return
            if isinstance(loaded, dict):
                self.data = loaded
            else:
                self.data = {"name": "", "entries": loaded if isinstance(loaded, list) else {}}
            if not isinstance(self.data.get("name"), str):
                self.data["name"] = ""
            self.convert_entries_to_dict()
            self.normalize_entries()
        except Exception as e:
            self.data = previous
            QMessageBox.critical(self, "Error", f"Failed to open JSON:\n{e}")
            return

        self.current_file = p
        self._loading = True
        try:
            self.lorebook_name.setText(self.data["name"])
        finally:
            self._loading = False
        self.dirty = False
        self.update_title()
        self.sync_ids_from_entries()
        self.renumber_uids()
        self.refresh()
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def save_file(self):
        self.data["name"] = self.lorebook_name.text()
        self.current_save()

        # Порядок списка и сплошные uid/id: 1, 2, 3...
        self.rebuild_entries_dict_order()
        self.renumber_uids()
        self.convert_entries_to_dict()

        lorebook_name = self.data.get("name", "").strip()
        safe_name = "".join(c for c in lorebook_name if c not in '\\/:*?"<>|' and ord(c) >= 32).strip().rstrip(".")
        if safe_name:
            name = f"{safe_name}.json"
        elif self.current_file:
            name = Path(self.current_file).name
        else:
            name = "lorebook.json"
        if self.current_file:
            name = str(Path(self.current_file).parent / name)

        p, _ = QFileDialog.getSaveFileName(self, "Save", name, "JSON (*.json)")
        if not p:
            return
        if not Path(p).suffix:
            p += ".json"
        try:
            save_json(p, self.data)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file:\n{e}")
            return
        self.current_file = p
        self.dirty = False
        self.update_title()

    # ---------- Entry CRUD ----------

    def add_entry(self):
        if self.search.text():
            self.search.clear()  # иначе новая запись сразу скрыта поиском
        entries = self.data.setdefault("entries", {})
        if not isinstance(entries, dict):
            entries = {}
            self.data["entries"] = entries

        existing = [int(x) for x in entries.keys() if str(x).isdigit()]
        nid = str(max(existing, default=0) + 1)

        entry_name = self.app_settings.get("new_entry_name", "New Entry") or "New Entry"
        entry = {"uid": int(nid), "id": int(nid), "name": entry_name}
        self.normalize_entry(nid, entry)  # все значения по умолчанию берутся из Settings
        entries[nid] = entry

        self.sync_ids_from_entries()
        self.dirty = True
        self.update_title()
        self.refresh()
        if self.ids:
            self.list.setCurrentRow(len(self.ids) - 1)

    def clone_entry(self):
        r = self.list.currentRow()
        if r < 0 or r >= len(self.ids):
            return
        entries = self.data.setdefault("entries", {})
        if not isinstance(entries, dict):
            return
        old_eid = self.ids[r]
        if old_eid not in entries:
            return

        existing = [int(x) for x in entries.keys() if str(x).isdigit()]
        nid = str(max(existing, default=0) + 1)

        entries[nid] = copy.deepcopy(entries[old_eid])
        entries[nid]["uid"] = int(nid)
        entries[nid]["id"] = int(nid)
        base_name = entries[nid].get("name") or entries[nid].get("comment") or "Entry"
        entries[nid]["name"] = f"{base_name} (Copy)"
        entries[nid]["comment"] = f"{base_name} (Copy)"

        # Клон ставим сразу после оригинала; renumber_uids() перенумерует ключи и uid по порядку.
        self.ids.insert(r + 1, nid)
        self.renumber_uids()
        self.dirty = True
        self.update_title()
        self.refresh()
        self.list.setCurrentRow(r + 1)

    def delete_entry(self):
        r = self.list.currentRow()
        if r < 0 or r >= len(self.ids):
            return
        eid = self.ids[r]
        name = self.data.get("entries", {}).get(eid, {}).get("name") or "Unnamed Entry"
        answer = QMessageBox.question(
            self,
            "Delete Entry",
            f"Delete entry \"{name}\"? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if answer != QMessageBox.Yes:
            return
        entries = self.data.get("entries", {})
        if eid in entries:
            del entries[eid]
        self.dirty = True
        self.update_title()
        self.sync_ids_from_entries()
        self.renumber_uids()
        self.refresh()  # при пустом списке сам очистит редактор
        if self.list.count() > 0:
            self.list.setCurrentRow(min(r, self.list.count() - 1))

    def save_entry(self):
        self.current_save()
        current = self.list.currentRow()
        self.refresh()
        if 0 <= current < self.list.count():
            self.list.setCurrentRow(current)

    # ---------- Ordering ----------

    def move_up(self):
        r = self.list.currentRow()
        if r <= 0:
            return
        self.ids[r - 1], self.ids[r] = self.ids[r], self.ids[r - 1]
        self.renumber_uids()
        self.dirty = True
        self.update_title()
        self.refresh()
        self.list.setCurrentRow(r - 1)

    def move_down(self):
        r = self.list.currentRow()
        if r < 0 or r >= len(self.ids) - 1:
            return
        self.ids[r + 1], self.ids[r] = self.ids[r], self.ids[r + 1]
        self.renumber_uids()
        self.dirty = True
        self.update_title()
        self.refresh()
        self.list.setCurrentRow(r + 1)

    def on_rows_moved(self, *args):
        """Drag & drop внутри списка. Перестраивать список прямо в обработчике сигнала нельзя:
        Qt ещё не закончил операцию drop, поэтому откладываем работу на следующий цикл событий."""
        if not self._reorder_pending:
            self._reorder_pending = True
            QTimer.singleShot(0, self._apply_rows_moved)

    def _apply_rows_moved(self):
        self._reorder_pending = False
        try:
            current = self.list.currentRow()
            self.sync_ids_from_list_widget()
            self.renumber_uids()
            self.dirty = True
            self.update_title()
            self.refresh()
            if 0 <= current < self.list.count():
                self.list.setCurrentRow(current)
            elif self.list.count() > 0:
                self.list.setCurrentRow(0)
        except Exception as ex:
            print("on_rows_moved error:", ex)

    def renumber_uids(self):
        """Fully renumber entries: rebuild the entries dict with new sequential keys (1,2,3...)
        according to current visual order in self.ids. Also updates uid/id fields.
        This ensures both the dictionary order and uid values match the UI order."""
        old_entries = self.data.get("entries", {})
        if not isinstance(old_entries, dict):
            return

        # Записи, которых нет в self.ids, не должны пропадать — дописываем их в конец.
        order = [eid for eid in self.ids if eid in old_entries]
        order += [eid for eid in old_entries if eid not in order]

        new_entries = {}
        new_ids = []

        for new_pos, old_eid in enumerate(order, start=1):
            entry = dict(old_entries[old_eid])  # copy
            new_key = str(new_pos)

            entry["uid"] = new_pos
            entry["id"] = new_pos
            if "displayIndex" in entry:
                entry["displayIndex"] = new_pos - 1

            new_entries[new_key] = entry
            new_ids.append(new_key)

        self.data["entries"] = new_entries
        self.ids = new_ids

    # ---------- Close handling ----------

    def closeEvent(self, event):
        if not self.dirty:
            event.accept()
            return
        r = QMessageBox.question(
            self,
            "Unsaved Changes",
            "Save changes before closing?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            QMessageBox.Yes
        )
        if r == QMessageBox.Cancel:
            event.ignore()
        elif r == QMessageBox.Yes:
            self.save_file()
            if not self.dirty:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def run():
    app = QApplication(sys.argv)
    app.setStyleSheet(get_dark_theme())
    w = MainWindow()
    w.show()
    code = app.exec()
    # Сигналы держат окно через лямбды, поэтому само оно не удаляется. Удаляем его явно,
    # пока QApplication ещё жив, иначе при выходе бывает Segmentation fault.
    shiboken6.delete(w)
    sys.exit(code)
