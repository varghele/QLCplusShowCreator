# gui/tabs/__init__.py

from .base_tab import BaseTab
from .configuration_tab import ConfigurationTab
from .fixtures_tab import FixturesTab
from .shows_tab_timeline import ShowsTabTimeline as ShowsTab  # Use timeline version
from .shows_tab_old import ShowsTab as ShowsTabOld  # Keep old version available
from .stage_tab import StageTab

__all__ = ['BaseTab', 'ConfigurationTab', 'FixturesTab', 'ShowsTab', 'ShowsTabOld', 'StageTab']
