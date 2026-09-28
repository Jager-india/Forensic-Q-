from django.apps import AppConfig


class QBankConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "q_bank"
    verbose_name = "Q-Bank"

    # Forensic Module Metadata
    module_num = "01"
    module_category = "TRANSACTION"
    module_name = "Bank"
    module_tag = "LIVE"
    module_accent = "orange"
    module_tagline = "Multi-Bank Forensic Analyzer"
    module_url = "/bank/"
    module_order = 1
