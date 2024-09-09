from django.apps import AppConfig
from openedx.core.djangoapps.plugins.constants import ProjectType, SettingsType


class IBLOpenedXScormXBlockConfig(AppConfig):
    name = "openedx_scorm_xblock"
    verbose_name = "IBL OpenedX Scorm XBlock"
    plugin_app = {}
