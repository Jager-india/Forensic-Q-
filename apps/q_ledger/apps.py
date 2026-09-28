from django.apps import AppConfig


class QLedgerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "q_ledger"
    verbose_name = "Q-Ledger"

    # Forensic Module Metadata (In Development)
    module_num = "08"
    module_category = "ERP / RECORDS"
    module_name = "Ledger"
    module_tag = "BUILDING"
    module_accent = "copper"
    module_tagline = "ERP Transaction Forensic Analyzer"
    module_url = "/demo/tabulator/"
    module_order = 8
