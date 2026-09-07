from pathlib import Path

def get_dark_theme(icons_dir: str | Path | None = None) -> str:
    """Return dark theme stylesheet with visible spinbox arrows and checkbox borders."""
    icons_dir = Path(icons_dir) if icons_dir else Path(__file__).parent / "icons"
    up = (icons_dir / "up.png").resolve().as_posix()
    down = (icons_dir / "down.png").resolve().as_posix()
    check = (icons_dir / "check.png").resolve().as_posix()

    return f'''
QWidget {{
    background: #1e1e1e;
    color: #ddd;
}}

QLineEdit, QTextEdit, QListWidget, QComboBox, QTextBrowser, QScrollArea, QDialog {{
    background: #2b2b2b;
    color: white;
    border: 1px solid #444;
}}

QSpinBox {{
    background: #2b2b2b;
    color: white;
    border: 1px solid #444;
    padding-right: 20px;
    min-height: 24px;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    subcontrol-origin: border;
    width: 18px;
    background: #3a3a3a;
    border: none;
    border-left: 1px solid #555;
}}

QSpinBox::up-button {{
    subcontrol-position: top right;
    border-top-right-radius: 2px;
}}

QSpinBox::down-button {{
    subcontrol-position: bottom right;
    border-bottom-right-radius: 2px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background: #505050;
}}

QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
    background: #606060;
}}

QSpinBox::up-arrow {{
    image: url("{up}");
    width: 10px;
    height: 10px;
}}

QSpinBox::down-arrow {{
    image: url("{down}");
    width: 10px;
    height: 10px;
}}

/* === Checkboxes: рамка всегда видна === */
QCheckBox {{
    spacing: 8px;
    color: #ddd;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid #777;
    border-radius: 3px;
    background: #2b2b2b;
}}

QCheckBox::indicator:unchecked {{
    background: #2b2b2b;
    border: 1px solid #777;
}}

QCheckBox::indicator:unchecked:hover {{
    border: 1px solid #999;
    background: #333;
}}

QCheckBox::indicator:checked {{
    background: #6a5acd;
    border: 1px solid #8f7cff;
    image: url("{check}");
}}

QCheckBox::indicator:checked:hover {{
    background: #7b6bde;
    border: 1px solid #a090ff;
}}

QPushButton {{
    background: #444;
    padding: 6px;
    border: 1px solid #666;
}}
QPushButton:hover {{
    background: #555;
}}

QTabBar::tab {{
    background: #353535;
    color: white;
    border: 1px solid #666;
    padding: 8px 16px;
}}
QTabBar::tab:selected {{
    background: #6a5acd;
    font-weight: bold;
}}

QListWidget {{
    padding: 4px;
}}
QListWidget::item {{
    border: 1px solid #555;
    margin: 4px;
    padding: 8px;
    border-radius: 4px;
    background: #323232;
    min-height: 24px;
}}
QListWidget::item:selected {{
    background: #6a5acd;
    color: white;
    border: 2px solid #8f7cff;
}}
'''
