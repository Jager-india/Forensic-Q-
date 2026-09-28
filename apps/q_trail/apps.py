from django.apps import AppConfig


class QTrailConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "q_trail"
    verbose_name = "Q-Trail"

    # Forensic Module Metadata
    module_num = "02"
    module_category = "TRANSACTION"
    module_name = "Trail"
    module_tag = "BUILDING"
    module_accent = "gold"
    module_tagline = "End-to-End Money Trail Mapper"
    module_url = "/demo/sandbox/"
    module_order = 2
