# gui/tabs/__init__.py

from .base_tab import BaseTab
from .configuration_tab import ConfigurationTab
from .fixtures_tab import FixturesTab
from .live_tab import LiveTab
from .shows_tab import ShowsTab
from .stage_tab import StageTab
from .structure_tab import StructureTab

__all__ = [
    'BaseTab', 'ConfigurationTab', 'FixturesTab', 'LiveTab',
    'ShowsTab', 'StageTab', 'StructureTab',
]
