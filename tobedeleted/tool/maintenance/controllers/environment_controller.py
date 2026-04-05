"""Environment controller compatibility facade.

Implementation is split under tool.maintenance.controllers.environment.* modules.
"""

from .environment.admin_ops import refresh_admin_tabs_impl
from .environment.config_ops import (
    init_field_states_impl,
    on_environment_changed_impl,
    save_config_impl,
)
from .environment.web_ops import (
    open_custom_url_impl,
    open_frontend_impl,
    open_portainer_impl,
    open_web_console_impl,
)

__all__ = [
    "refresh_admin_tabs_impl",
    "on_environment_changed_impl",
    "init_field_states_impl",
    "save_config_impl",
    "open_frontend_impl",
    "open_portainer_impl",
    "open_web_console_impl",
    "open_custom_url_impl",
]

