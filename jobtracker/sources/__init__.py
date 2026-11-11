from .base import Source, SourceSkipped
from .vc_boards import VcBoardsSource

SOURCES: dict[str, type[Source]] = {cls.name: cls for cls in (VcBoardsSource,)}

__all__ = ["SOURCES", "Source", "SourceSkipped"]
