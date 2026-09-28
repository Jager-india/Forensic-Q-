"""
Q-Chat Database Models
Stores corporate chat channels, instant messaging threads, attachments, and risk flags.
"""

from django.db import models

from core.models import ForensicBaseModel


class ChatChannel(ForensicBaseModel):
    """
    Forensic Chat Channel / Conversation Thread.
    Can originate from WhatsApp, Teams, Slack, Telegram, or SMS export files.
    """

    class Platform(models.TextChoices):
        WHATSAPP = "WHATSAPP", "WhatsApp"
        TEAMS = "TEAMS", "Microsoft Teams"
        SLACK = "SLACK", "Slack"
        TELEGRAM = "TELEGRAM", "Telegram"
        SMS = "SMS", "SMS / iMessage"

    platform = models.CharField(
        max_length=32,
        choices=Platform.choices,
        default=Platform.WHATSAPP,
        db_index=True,
    )
    channel_name = models.CharField(
        max_length=255, db_index=True, help_text="Channel Title or Contact Name"
    )
    custodian_name = models.CharField(
        max_length=255, blank=True, default="", help_text="Device Custodian / Auditee"
    )
    is_direct_message = models.BooleanField(default=False)
    participant_count = models.IntegerField(default=2)
    participants = models.JSONField(default=list, help_text="List of participant names/handles")
    total_messages = models.IntegerField(default=0)
    flagged_messages_count = models.IntegerField(default=0)
    source_filename = models.CharField(max_length=255, blank=True, default="")
    first_message_at = models.DateTimeField(null=True, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    risk_score = models.IntegerField(default=0, db_index=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        app_label = "q_chat"
        ordering = ["-last_message_at", "-created_at"]
        verbose_name = "Chat Channel"
        verbose_name_plural = "Chat Channels"

    def __str__(self) -> str:
        return f"[{self.get_platform_display()}] {self.channel_name} ({self.total_messages} msgs)"


class ChatMessage(ForensicBaseModel):
    """
    Individual chat message record within a conversation channel.
    """

    class MediaType(models.TextChoices):
        NONE = "NONE", "Text Only"
        IMAGE = "IMAGE", "Image"
        DOCUMENT = "DOCUMENT", "Document / PDF"
        AUDIO = "AUDIO", "Voice Note / Audio"
        VIDEO = "VIDEO", "Video"

    channel = models.ForeignKey(
        ChatChannel,
        on_delete=models.CASCADE,
        related_name="messages",
        help_text="Originating Conversation Channel",
    )
    sender_name = models.CharField(max_length=255, db_index=True, help_text="Sender Display Name")
    sender_handle = models.CharField(
        max_length=128, blank=True, default="", help_text="Phone / Email / Username"
    )
    sent_at = models.DateTimeField(db_index=True)
    message_text = models.TextField(blank=True, default="")
    has_media = models.BooleanField(default=False, db_index=True)
    media_type = models.CharField(
        max_length=16,
        choices=MediaType.choices,
        default=MediaType.NONE,
    )
    media_filename = models.CharField(max_length=255, blank=True, default="")
    media_path = models.CharField(max_length=1024, blank=True, default="")
    is_deleted = models.BooleanField(
        default=False, db_index=True, help_text="Message was deleted or retracted"
    )
    is_edited = models.BooleanField(default=False)
    risk_score = models.IntegerField(default=0, db_index=True)
    flagged_terms = models.JSONField(default=list)
    reply_to_sender = models.CharField(max_length=255, blank=True, default="")
    reply_to_text = models.TextField(blank=True, default="")
    raw_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        app_label = "q_chat"
        ordering = ["sent_at", "created_at"]
        verbose_name = "Chat Message"
        verbose_name_plural = "Chat Messages"

    def __str__(self) -> str:
        return f"{self.sent_at} | {self.sender_name}: {self.message_text[:30]}"


class ChatWatchlistRule(ForensicBaseModel):
    """
    Watchlist rules for screening instant messages for collusion, bribery, and off-the-record terms.
    """

    rule_name = models.CharField(max_length=128)
    keyword = models.CharField(max_length=128, db_index=True)
    risk_weight = models.IntegerField(default=50)
    category = models.CharField(max_length=64, default="Collusion")
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "q_chat"
        ordering = ["-risk_weight", "rule_name"]
        verbose_name = "Chat Watchlist Rule"
        verbose_name_plural = "Chat Watchlist Rules"

    def __str__(self) -> str:
        return f"[{self.category}] {self.keyword} (+{self.risk_weight})"
