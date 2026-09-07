import sys
import copy
import markdown
from PySide6.QtCore import QTimer, Qt
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
from .settings import load_settings, save_settings, SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1600, 900)
        self.setWindowTitle("Lorebook Studio 1.0")

        self.data = {"name": "Lorebook", "entries": {}}
        self.ids = []
        self.current_file = None
        self.dirty = False
        self._loading = False
        self.app_settings = load_settings()

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)

        left = QVBoxLayout()
        self.lorebook_name = QLineEdit()
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
        self.insertion_order.setRange(0, 9999)
        self.insertion_order.setSingleStep(1)
        self.insertion_order.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.priority = QSpinBox()
        self.priority.setRange(0, 999)
        self.priority.setSingleStep(1)
        self.priority.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.depth = QSpinBox()
        self.depth.setRange(0, 99)
        self.depth.setSingleStep(1)
        self.depth.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)
        self.probability = QSpinBox()
        self.probability.setRange(0, 100)
        self.probability.setSingleStep(1)
        self.probability.setButtonSymbols(QSpinBox.ButtonSymbols.UpDownArrows)

        self.case_sensitive = QCheckBox()
        self.exclude_recursion = QCheckBox("")
        self.selective = QCheckBox()
        self.constant = QCheckBox()
        self.enabled = QCheckBox()

        self.selective_logic = QComboBox()
        self.selective_logic.addItems(["AND", "NOT"])

        self.content = QTextEdit()
        self.counter_label = QLabel("Characters: 0 | Tokens: 0")
        self.lorebook_stats_label = QLabel("Lorebook Statistics: Entries 0 | Characters 0 | Tokens 0")

        self.preview_timer = QTimer(self)
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_preview)
        self.content.textChanged.connect(lambda: self.preview_timer.start(300))
        self.content.textChanged.connect(self.update_counter)
        self.content.textChanged.connect(self.update_current_item_info)

        for w in [self.name, self.keys, self.secondary]:
            w.textChanged.connect(self.current_save)
        self.content.textChanged.connect(self.current_save)
        for w in [self.case_sensitive, self.exclude_recursion, self.selective, self.constant, self.enabled]:
            w.stateChanged.connect(self.current_save)
        for w in [self.insertion_order, self.priority, self.depth, self.probability]:
            w.valueChanged.connect(self.current_save)
        self.selective_logic.currentIndexChanged.connect(self.current_save)

        field_hints = [
            ("Name", self.name, "Display name of this entry. Also saved as comment for other editors."),
            ("Keywords", self.keys, "The keys that activate the content."),
            ("Secondary Keywords", self.secondary, "Additional keys required to activate the content. Ignored if Selective is off."),
            ("Insertion Order", self.insertion_order, "If multiple entries are inserted, lower Insertion Order is inserted higher."),
            ("Case Sensitive", self.case_sensitive, "Whether the keywords are case-sensitive."),
            ("Non-recursable", self.exclude_recursion, "Prevent this entry from being activated by other lorebook entries."),
            ("Priority", self.priority, "If the token budget is reached, lower priority is discarded first."),
            ("Selective", self.selective, "Require both keywords and secondary keywords to trigger the entry."),
            ("Selective Logic", self.selective_logic, "AND includes secondary keys, NOT excludes them. Ignored if Selective is off."),
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
            self.setWindowTitle(f"Lorebook Studio by Egohox - {lorebook} *")
        else:
            self.setWindowTitle(f"Lorebook Studio by Egohox - {lorebook}")

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
            name = e.get("name") or e.get("comment") or str(eid)
            content = str(e.get("content", ""))
            chars = len(content)

            kw = e.get("keys", e.get("key", []))
            if isinstance(kw, str):
                kw_count = len([x for x in kw.split(",") if x.strip()])
            elif isinstance(kw, list):
                kw_count = len(kw)
            else:
                kw_count = 0

            tokens = max(0, chars // 4)
            label = f"{idx}. {name}\n{chars} chars | {tokens} tokens | {kw_count} keywords"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, eid)
            self.list.addItem(item)

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
                item.text(),
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
            self.name.setText(e.get("name", ""))
            keys_val = e.get("key", e.get("keys", []))
            if isinstance(keys_val, list):
                self.keys.setText(",".join(keys_val))
            else:
                self.keys.setText(str(keys_val) if keys_val else "")

            sec_val = e.get("secondary_keys", e.get("keysecondary", []))
            if isinstance(sec_val, list):
                self.secondary.setText(",".join(sec_val))
            else:
                self.secondary.setText(str(sec_val) if sec_val else "")

            self.insertion_order.setValue(int(e.get("insertion_order", e.get("order", 100))))
            self.case_sensitive.setChecked(bool(e.get("case_sensitive", False)))
            self.exclude_recursion.setChecked(bool(e.get("excludeRecursion", False)))
            self.priority.setValue(int(e.get("priority", 10)))
            self.selective.setChecked(bool(e.get("selective", False)))
            self.selective_logic.setCurrentIndex(int(e.get("selectiveLogic", 0)))
            self.constant.setChecked(bool(e.get("constant", False)))
            self.probability.setValue(int(e.get("probability", 100)))
            self.depth.setValue(int(e.get("depth", 0)))
            self.enabled.setChecked(bool(e.get("enabled", True)))
            self.content.setPlainText(e.get("content", ""))
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
        text = self.content.toPlainText()
        chars = len(text)
        tokens = max(0, chars // 4)
        self.counter_label.setText(f"Characters: {chars} | Tokens: {tokens}")
        self.update_lorebook_stats()

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
        try:
            row = self.list.currentRow()
            if row < 0 or row >= len(self.ids):
                return
            eid = self.ids[row]
            entries = self.data.get("entries", {})
            e = entries.get(eid, {})

            name = self.name.text() or e.get("name") or "Unnamed Entry"
            chars = len(self.content.toPlainText())
            tokens = max(0, chars // 4)

            kw = e.get("keys", e.get("key", []))
            if isinstance(kw, str):
                kw_count = len([x for x in kw.split(",") if x.strip()])
            elif isinstance(kw, list):
                kw_count = len(kw)
            else:
                kw_count = 0

            item = self.list.item(row)
            if item:
                item.setText(f"{row + 1}. {name}\n{chars} chars | {tokens} tokens | {kw_count} keywords")
        except Exception as ex:
            print("update_current_item_info error:", ex)

    # ---------- Save current editor state to data ----------

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

        kw = [x.strip() for x in self.keys.text().split(",") if x.strip()]
        sk = [x.strip() for x in self.secondary.text().split(",") if x.strip()]

        e["name"] = self.name.text()
        e["comment"] = self.name.text()  # Всегда синхронизируем (редакторы берут либо name, либо comment)
        e["key"] = kw
        e["keys"] = kw
        e["keysecondary"] = sk
        e["secondary_keys"] = sk
        e["insertion_order"] = self.insertion_order.value()
        e["order"] = self.insertion_order.value()
        e["case_sensitive"] = self.case_sensitive.isChecked()
        e["excludeRecursion"] = self.exclude_recursion.isChecked()
        e.setdefault("extensions", {})["excludeRecursion"] = self.exclude_recursion.isChecked()
        e["priority"] = self.priority.value()
        e["selective"] = self.selective.isChecked()
        e["selectiveLogic"] = self.selective_logic.currentIndex()
        e["constant"] = self.constant.isChecked()
        e["probability"] = self.probability.value()
        e["depth"] = self.depth.value()
        e["enabled"] = self.enabled.isChecked()
        e["content"] = self.content.toPlainText()

        e.setdefault("extensions", {})
        e["extensions"]["depth"] = self.depth.value()
        e["extensions"]["weight"] = self.priority.value()
        e["extensions"]["probability"] = self.probability.value()
        e["extensions"]["useProbability"] = True
        e["extensions"]["selectiveLogic"] = self.selective_logic.currentIndex()

        self.update_current_item_info()
        self.dirty = True
        self.update_title()

    # ---------- Entry conversion (list -> dict) ----------

    def convert_entries_to_dict(self):
        """Convert legacy list of entries into dict keyed by UID (string keys)."""
        entries = self.data.get("entries", {})
        if isinstance(entries, dict):
            return
        if not isinstance(entries, list):
            self.data["entries"] = {}
            return

        new_entries = {}
        used = set()
        for i, e in enumerate(entries):
            if not isinstance(e, dict):
                continue
            raw = e.get("uid", e.get("id", i + 1))
            try:
                uid = str(int(raw))
            except (ValueError, TypeError):
                uid = str(i + 1)
            while uid in used:
                uid = str(int(uid) + 1)
            used.add(uid)

            e = copy.deepcopy(e)
            e["uid"] = int(uid)
            e["id"] = int(uid)

            if not e.get("name"):
                e["name"] = e.get("comment", f"Entry {uid}")
            if not e.get("comment"):
                e["comment"] = e.get("name", f"Entry {uid}")

            new_entries[uid] = e

        self.data["entries"] = new_entries

    def normalize_entries(self):
        """Ensure every entry has all required Chub fields with sane defaults.
        Also forces name == comment for cross-editor compatibility."""
        entries = self.data.get("entries", {})
        if not isinstance(entries, dict):
            return
        for e in entries.values():
            if not isinstance(e, dict):
                continue

            # Синхронизация name и comment
            if e.get("name"):
                e["comment"] = e["name"]
            elif e.get("comment"):
                e["name"] = e["comment"]

            s = self.app_settings
            e.setdefault("selective", s.get("selective", False))
            e.setdefault("case_sensitive", s.get("case_sensitive", False))
            e.setdefault("priority", s.get("priority", 10))
            e.setdefault("probability", s.get("probability", 100))
            e.setdefault("useProbability", s.get("useProbability", True))
            e.setdefault("enabled", s.get("enabled", True))
            e.setdefault("disable", s.get("disable", False))
            e.setdefault("constant", s.get("constant", False))
            e.setdefault("selectiveLogic", s.get("selectiveLogic", 0))
            e.setdefault("addMemo", s.get("addMemo", True))
            e.setdefault("excludeRecursion", s.get("excludeRecursion", False))
            e.setdefault("depth", s.get("depth", 0))
            e.setdefault("order", s.get("insertion_order", 100))
            e.setdefault("insertion_order", s.get("insertion_order", 100))
            ext = e.setdefault("extensions", {})
            ext.setdefault("depth", s.get("depth", 0))
            ext.setdefault("weight", s.get("priority", 10))
            ext.setdefault("probability", s.get("probability", 100))
            ext.setdefault("useProbability", s.get("useProbability", True))
            ext.setdefault("selectiveLogic", s.get("selectiveLogic", 0))
            ext.setdefault("addMemo", s.get("addMemo", True))
            ext.setdefault("excludeRecursion", s.get("excludeRecursion", False))

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

        try:
            self.list.clear()
        except Exception:
            pass

        self._loading = True
        try:
            s = self.app_settings
            self.lorebook_name.setText("Lorebook")
            self.name.clear()
            self.keys.clear()
            self.secondary.clear()
            self.content.clear()
            self.insertion_order.setValue(int(s.get("insertion_order", 100)))
            self.priority.setValue(int(s.get("priority", 10)))
            self.depth.setValue(int(s.get("depth", 0)))
            self.probability.setValue(int(s.get("probability", 100)))
            self.case_sensitive.setChecked(bool(s.get("case_sensitive", False)))
            self.exclude_recursion.setChecked(bool(s.get("excludeRecursion", False)))
            self.selective.setChecked(bool(s.get("selective", False)))
            self.selective_logic.setCurrentIndex(int(s.get("selectiveLogic", 0)))
            self.constant.setChecked(bool(s.get("constant", False)))
            self.enabled.setChecked(bool(s.get("enabled", True)))
        finally:
            self._loading = False

        self.update_title()
        self.update_preview()
        self.update_counter()
        self.update_lorebook_stats()

    def open_settings(self):
        dlg = SettingsDialog(self, self.app_settings)
        if dlg.exec():
            self.app_settings = dlg.values()
            save_settings(self.app_settings)

    def open_file(self):
        if self.dirty:
            r = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Save changes before opening another lorebook?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            if r == QMessageBox.Cancel:
                return
            if r == QMessageBox.Yes:
                self.save_file()
                if self.dirty:
                    return

        p, _ = QFileDialog.getOpenFileName(self, "Open", "", "JSON (*.json)")
        if not p:
            return
        try:
            loaded = load_json(p)
            if isinstance(loaded, dict):
                self.data = loaded
            else:
                self.data = {"name": "", "entries": loaded if isinstance(loaded, list) else {}}
            self.convert_entries_to_dict()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open JSON:\n{e}")
            return

        self.normalize_entries()
        self.current_file = p
        self._loading = True
        try:
            self.lorebook_name.setText(self.data.get("name", ""))
        finally:
            self._loading = False
        self.dirty = False
        self.update_title()
        self.sync_ids_from_entries()
        self.refresh()
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def save_file(self):
        self.data["name"] = self.lorebook_name.text()
        self.current_save()

        # Важно: пересобираем словарь entries в порядке self.ids,
        # чтобы в сохранённом JSON записи шли в том порядке, в котором их расположил пользователь.
        self.rebuild_entries_dict_order()

        self.convert_entries_to_dict()

        assert isinstance(self.data, dict)
        assert "entries" in self.data
        assert isinstance(self.data["entries"], dict)

        # Final safety pass
        for eid, e in list(self.data.get("entries", {}).items()):
            if isinstance(e, dict):
                if not e.get("name"):
                    e["name"] = e.get("comment", f"Entry {eid}")
                if not e.get("comment"):
                    e["comment"] = e.get("name", f"Entry {eid}")

        lorebook_name = self.data.get("name", "").strip()
        if lorebook_name:
            safe_name = "".join(c for c in lorebook_name if c not in '\\/:*?"<>|')
            name = f"{safe_name}.json"
        elif self.current_file:
            o = Path(self.current_file)
            name = o.name
        else:
            name = "lorebook.json"

        p, _ = QFileDialog.getSaveFileName(self, "Save", name, "JSON (*.json)")
        if p:
            save_json(p, self.data)
            self.current_file = p
            self.dirty = False
            self.update_title()

    # ---------- Entry CRUD ----------

    def add_entry(self):
        entries = self.data.setdefault("entries", {})
        if not isinstance(entries, dict):
            entries = {}
            self.data["entries"] = entries

        existing = [int(x) for x in entries.keys() if str(x).isdigit()]
        nid = str(max(existing, default=0) + 1)

        s = self.app_settings
        entry_name = s.get("new_entry_name", "New Entry") or "New Entry"
        entries[nid] = {
            "uid": int(nid),
            "id": int(nid),
            "name": entry_name,
            "comment": entry_name,
            "key": [],
            "keys": [],
            "keysecondary": [],
            "secondary_keys": [],
            "enabled": s.get("enabled", True),
            "disable": s.get("disable", False),
            "case_sensitive": s.get("case_sensitive", False),
            "priority": s.get("priority", 10),
            "selective": s.get("selective", False),
            "selectiveLogic": s.get("selectiveLogic", 0),
            "constant": s.get("constant", False),
            "probability": s.get("probability", 100),
            "useProbability": s.get("useProbability", True),
            "depth": s.get("depth", 0),
            "addMemo": s.get("addMemo", True),
            "excludeRecursion": s.get("excludeRecursion", False),
            "order": s.get("insertion_order", 100),
            "insertion_order": s.get("insertion_order", 100),
            "content": "",
            "extensions": {
                "depth": s.get("depth", 0),
                "weight": s.get("priority", 10),
                "probability": s.get("probability", 100),
                "useProbability": s.get("useProbability", True),
                "selectiveLogic": s.get("selectiveLogic", 0),
                "addMemo": s.get("addMemo", True),
                "excludeRecursion": s.get("excludeRecursion", False)
            }
        }
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

        self.sync_ids_from_entries()
        self.refresh()
        self.dirty = True
        self.update_title()
        if self.ids:
            self.list.setCurrentRow(len(self.ids) - 1)

    def delete_entry(self):
        r = self.list.currentRow()
        if r < 0 or r >= len(self.ids):
            return
        eid = self.ids[r]
        entries = self.data.get("entries", {})
        if eid in entries:
            del entries[eid]
        self.dirty = True
        self.update_title()
        self.sync_ids_from_entries()
        self.refresh()
        if self.list.count() > 0:
            self.list.setCurrentRow(min(r, self.list.count() - 1))
        else:
            self.name.clear()
            self.keys.clear()
            self.secondary.clear()
            self.content.clear()

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

    def on_rows_moved(self, parent, start, end, destination, row):
        """Called after drag & drop reorder inside the list."""
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

        new_entries = {}
        new_ids = []

        for new_pos, old_eid in enumerate(self.ids, start=1):
            if old_eid not in old_entries:
                continue

            entry = dict(old_entries[old_eid])  # copy
            new_key = str(new_pos)

            entry["uid"] = new_pos
            entry["id"] = new_pos

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
    sys.exit(app.exec())
