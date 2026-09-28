from django.apps import AppConfig


class QMailConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "q_mail"
    verbose_name = "Q-Mail"

    # Forensic Module Metadata
    module_num = "03"
    module_category = "COMMUNICATIONS"
    module_name = "Mail"
    module_tag = "LIVE"
    module_accent = "purple"
    module_tagline = "Email Forensic Intelligence Analyzer"
    module_url = "/mail/"
    module_order = 3
