import json
import os
import tempfile


def load_json(path):
    # utf-8-sig: корректно читает и обычные файлы, и файлы с BOM (Блокнот Windows и др.)
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _default_file_mode() -> int:
    umask = os.umask(0)
    os.umask(umask)
    return 0o666 & ~umask


def save_json(path, data):
    path = os.fspath(path)
    directory = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        # mkstemp создаёт файл с правами 0600 — сохраняем права исходного файла
        # (или обычные права по umask для нового файла).
        try:
            mode = os.stat(path).st_mode & 0o777
        except OSError:
            mode = _default_file_mode()
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
