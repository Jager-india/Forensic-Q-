from django.apps import AppConfig


class QScanConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "q_scan"
    verbose_name = "Q-Scan"

    # Forensic Module Metadata
    module_num = "04"
    module_category = "DESKTOP"
    module_name = "Scan"
    module_tag = "LIVE"
    module_accent = "teal"
    module_tagline = "Computer Evidence Discovery Tool"
    module_url = "/scan/"
    module_order = 4
