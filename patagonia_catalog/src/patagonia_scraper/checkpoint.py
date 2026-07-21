from __future__ import annotations

import json
import logging
import threading
from dataclasses import asdict
from pathlib import Path

from .models import OUTPUT_COLUMNS, ProductRow

LOGGER = logging.getLogger(__name__)


class Checkpoint:
    """Crash-safe, append-only record of successfully scraped products.

    Each completed product writes one JSON line ``{"url", "rows"}`` and is
    flushed immediately, so closing the window mid-run never loses finished
    products. On the next run the same file is loaded and those URLs are
    skipped, letting the scrape resume where it stopped.
    """

    def __init__(self, path: Path, enabled: bool = True) -> None:
        self.path = Path(path)
        self.enabled = enabled
        self._lock = threading.Lock()
        self._done: dict[str, list[dict]] = {}
        if enabled and self.path.exists():
            self._load()

    def _load(self) -> None:
        loaded = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            url = obj.get("url")
            rows = obj.get("rows")
            if url and isinstance(rows, list):
                self._done[url] = rows
                loaded += 1
        if loaded:
            LOGGER.info("Loaded %s completed products from %s", loaded, self.path.name)

    def is_done(self, key: str) -> bool:
        return key in self._done

    @property
    def done_count(self) -> int:
        return len(self._done)

    def add(self, key: str, rows: list[ProductRow]) -> int:
        """Record a product's rows and append them to disk. Returns total done."""
        data = [asdict(row) for row in rows]
        with self._lock:
            self._done[key] = data
            if self.enabled:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with self.path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"url": key, "rows": data}, ensure_ascii=False) + "\n")
                    handle.flush()
            return len(self._done)

    def all_rows(self) -> list[ProductRow]:
        with self._lock:
            snapshot = list(self._done.values())
        rows: list[ProductRow] = []
        for data in snapshot:
            for item in data:
                rows.append(ProductRow(**{col: item.get(col, "") for col in OUTPUT_COLUMNS}))
        return rows

    def remove(self) -> None:
        try:
            self.path.unlink()
        except Exception:
            pass
