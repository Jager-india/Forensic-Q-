from django.apps import AppConfig


class QVoiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "q_voice"
    verbose_name = "Q-Voice"

    # Forensic Module Metadata
    module_num = "07"
    module_category = "VOICE"
    module_name = "Voice"
    module_tag = "LIVE"
    module_accent = "indigo"
    module_tagline = "Voice Transcript Intelligence Analyzer"
    module_url = "/voice/"
    module_order = 7
