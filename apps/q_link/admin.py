from django.contrib import admin

from .models import (
    EntityAlias,
    EntityRelationship,
    EvidencePointer,
    ForensicEntity,
    ForensicTimelineEvent,
    RelationshipAlert,
)


@admin.register(ForensicEntity)
class ForensicEntityAdmin(admin.ModelAdmin):
    list_display = (
        "display_name",
        "entity_type",
        "identifier",
        "risk_rating",
        "is_target",
        "created_at",
    )
    list_filter = ("entity_type", "is_target", "category")
    search_fields = ("display_name", "identifier")


@admin.register(EntityAlias)
class EntityAliasAdmin(admin.ModelAdmin):
    list_display = ("alias_name", "entity", "match_source", "confidence", "created_at")
    list_filter = ("match_source",)
    search_fields = ("alias_name", "entity__display_name")


@admin.register(EntityRelationship)
class EntityRelationshipAdmin(admin.ModelAdmin):
    list_display = (
        "source_entity",
        "relation_type",
        "target_entity",
        "confidence_score",
        "weight",
        "source_module",
        "is_direct",
    )
    list_filter = ("relation_type", "source_module", "is_direct")
    search_fields = ("source_entity__display_name", "target_entity__display_name")


@admin.register(EvidencePointer)
class EvidencePointerAdmin(admin.ModelAdmin):
    list_display = (
        "source_module",
        "source_model",
        "source_record_id",
        "occurred_at",
        "relationship",
    )
    list_filter = ("source_module", "source_model")
    search_fields = ("source_record_id", "summary_snippet")


@admin.register(ForensicTimelineEvent)
class ForensicTimelineEventAdmin(admin.ModelAdmin):
    list_display = ("event_timestamp", "event_title", "entity", "source_module", "severity")
    list_filter = ("source_module", "severity")
    search_fields = ("event_title", "entity__display_name")


@admin.register(RelationshipAlert)
class RelationshipAlertAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "alert_level",
        "primary_entity",
        "risk_score",
        "is_acknowledged",
        "created_at",
    )
    list_filter = ("alert_level", "is_acknowledged")
    search_fields = ("title", "trigger_reason", "ai_summary")
