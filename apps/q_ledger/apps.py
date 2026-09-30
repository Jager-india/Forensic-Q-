from django.apps import AppConfig


class QLedgerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "q_ledger"
    verbose_name = "Q-Ledger"

    # Forensic Module Metadata
    module_num = "08"
    module_category = "ERP / RECORDS"
    module_name = "Ledger"
    module_tag = "LIVE"
    module_accent = "copper"
    module_tagline = "SAP ERP & Procurement Forensic Analyzer"
    module_url = "/ledger/"
    module_order = 8
