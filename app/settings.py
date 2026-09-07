import json
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox,
    QLineEdit, QSpinBox, QCheckBox, QComboBox, QLabel, QWidget,
    QScrollArea, QSizePolicy
)


DEFAULTS = {
    "new_entry_name": "New Entry",
    "insertion_order": 100,
    "priority": 10,
    "depth": 0,
    "probability": 100,
    "enabled": True,
    "disable": False,
    "case_sensitive": False,
    "selective": False,
    "constant": False,
    "excludeRecursion": False,
    "useProbability": True,
    "addMemo": True,
    "selectiveLogic": 0,
}


def settings_path() -> Path:
    return Path(__file__).resolve().parent.parent / "settings.json"


def load_settings() -> dict:
    data = dict(DEFAULTS)
    path = settings_path()
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                for key, default in DEFAULTS.items():
                    if key in loaded and type(loaded[key]) is type(default):
                        data[key] = loaded[key]
        except Exception:
            pass
    return data


def save_settings(data: dict) -> None:
    merged = dict(DEFAULTS)
    merged.update(data)
    path = settings_path()
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")


def _hinted(widget, hint: str) -> QWidget:
    box = QWidget()
    box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(2)
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout.addWidget(widget)
    label = QLabel(hint)
    label.setWordWrap(True)
    label.setStyleSheet("color: #888; font-size: 11px;")
    layout.addWidget(label)
    widget.setToolTip(hint)
    return box


class SettingsDialog(QDialog):
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self.setMinimumHeight(400)
        self.resize(520, 700)
        self.settings = dict(DEFAULTS)
        if isinstance(settings, dict):
            self.settings.update(settings)

        layout = QVBoxLayout(self)

        hint = QLabel(
            "Default values for new entries (+) and for missing fields when importing a lorebook."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        inner = QWidget()
        form = QFormLayout(inner)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        form.setVerticalSpacing(10)

        self.new_entry_name = QLineEdit()
        self.new_entry_name.setText(str(self.settings.get("new_entry_name", "New Entry")))

        self.insertion_order = QSpinBox()
        self.insertion_order.setRange(0, 9999)
        self.insertion_order.setValue(int(self.settings.get("insertion_order", 100)))

        self.priority = QSpinBox()
        self.priority.setRange(0, 999)
        self.priority.setValue(int(self.settings.get("priority", 10)))

        self.depth = QSpinBox()
        self.depth.setRange(0, 99)
        self.depth.setValue(int(self.settings.get("depth", 0)))

        self.probability = QSpinBox()
        self.probability.setRange(0, 100)
        self.probability.setValue(int(self.settings.get("probability", 100)))

        self.selective_logic = QComboBox()
        self.selective_logic.addItems(["AND", "NOT"])
        idx = int(self.settings.get("selectiveLogic", 0))
        self.selective_logic.setCurrentIndex(0 if idx not in (0, 1) else idx)

        self.enabled = QCheckBox()
        self.enabled.setChecked(bool(self.settings.get("enabled", True)))
        self.disable = QCheckBox()
        self.disable.setChecked(bool(self.settings.get("disable", False)))
        self.case_sensitive = QCheckBox()
        self.case_sensitive.setChecked(bool(self.settings.get("case_sensitive", False)))
        self.selective = QCheckBox()
        self.selective.setChecked(bool(self.settings.get("selective", False)))
        self.constant = QCheckBox()
        self.constant.setChecked(bool(self.settings.get("constant", False)))
        self.exclude_recursion = QCheckBox()
        self.exclude_recursion.setChecked(bool(self.settings.get("excludeRecursion", False)))
        self.use_probability = QCheckBox()
        self.use_probability.setChecked(bool(self.settings.get("useProbability", True)))

        for label, widget, text in [
            ("Name", self.new_entry_name, "Display name of this entry. Also saved as comment for other editors."),
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
            ("Disable", self.disable, "Compatibility flag for some editors. Keep off unless you need it."),
            ("Use Probability", self.use_probability, "If on, the Probability value is used. If off, Probability is ignored."),
        ]:
            form.addRow(label, _hinted(widget, text))

        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> dict:
        return {
            "new_entry_name": self.new_entry_name.text().strip() or "New Entry",
            "insertion_order": self.insertion_order.value(),
            "priority": self.priority.value(),
            "depth": self.depth.value(),
            "probability": self.probability.value(),
            "selectiveLogic": self.selective_logic.currentIndex(),
            "enabled": self.enabled.isChecked(),
            "disable": self.disable.isChecked(),
            "case_sensitive": self.case_sensitive.isChecked(),
            "selective": self.selective.isChecked(),
            "constant": self.constant.isChecked(),
            "excludeRecursion": self.exclude_recursion.isChecked(),
            "useProbability": self.use_probability.isChecked(),
            "addMemo": True,
        }
