from django.apps import AppConfig


class QChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "q_chat"
    verbose_name = "Q-Chat"

    # Forensic Module Metadata (In Development)
    module_num = "09"
    module_category = "COMMUNICATIONS"
    module_name = "Chat"
    module_tag = "LIVE"
    module_accent = "steel"
    module_tagline = "Corporate Chat Forensic Analyzer"
    module_url = "/chat/"
    module_order = 9
