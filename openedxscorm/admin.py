from django.contrib import admin

from . import models


@admin.register(models.ScormState)
class ScormStateAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "course_key", "usage_key")


@admin.register(models.ScormInteraction)
class ScormInteractionAdmin(admin.ModelAdmin):
    list_display = ("id", "scorm_state", "interaction_id", "index")
