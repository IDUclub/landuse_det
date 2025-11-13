from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path


class Cacheable(ABC):
    @abstractmethod
    def to_file(self, path: Path, name: str, date: datetime, *args) -> None:
        pass
