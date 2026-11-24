"""Caminhos independentes do diretório de trabalho e compatíveis com PyInstaller."""

from dataclasses import dataclass
from pathlib import Path
import sys


@dataclass(frozen=True)
class AppPaths:
    root: Path

    @classmethod
    def discover(cls, base_dir=None):
        if base_dir is not None:
            return cls(Path(base_dir).resolve())
        if getattr(sys, "frozen", False):
            return cls(Path(sys.executable).resolve().parent)
        return cls(Path(__file__).resolve().parent.parent)

    @property
    def config(self):
        return self.root / "config.json"

    @property
    def database(self):
        return self.root / "data" / "agroclima.db"

    @property
    def logs(self):
        return self.root / "logs"

    @property
    def resources(self):
        return Path(__file__).resolve().parent

    @property
    def stylesheet(self):
        return self.resources / "styles" / "theme.qss"
