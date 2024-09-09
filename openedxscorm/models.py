from django.contrib.auth.models import User
from django.db import models
from opaque_keys.edx.django.models import CourseKeyField


class ScormState(models.Model):
    class CompleteChoices(models.TextChoices):
        COMPLETED = "completed"
        INCOMPLETE = "incomplete"
        UNKNOWN = "unknown"

    class SuccessChoices(models.TextChoices):
        PASSED = "passed"
        FAILED = "failed"
        UNKNOWN = "unknown"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course_key = CourseKeyField(
        max_length=255,
        unique=True,
        help_text="example: course-v1:Org+Course+Run",
    )
    block_id = models.CharField(max_length=255, blank=True, null=True, unique=True)

    success_status = models.CharField(
        max_length=7, default="", choices=SuccessChoices.choices
    )
    complete_status = models.CharField(
        max_length=10, default="", choices=CompleteChoices.choices
    )
    lession_score = models.FloatField(blank=True, null=True)
    session_times = models.JSONField(default=lambda: [])
    timestamp = models.DateTimeField(auto_now=True)


class ScormInteraction(models.Model):
    class TypeChoices(models.TextChoices):
        TRUE_FALSE = "true-false"
        CHOICE = "choice"
        FILL_IN = "fill-in"
        MATCHING = "matching"
        PERFORMANCE = "performance"
        SEQUENCING = "sequencing"
        LIKERT = "likert"
        NUMERIC = "numeric"

    scorm_state = models.ForeignKey(
        ScormState, on_delete=models.CASCADE, related_name="scorm_interactions"
    )
    interaction_id = models.CharField(max_length=255)
    index = models.IntegerField()
    type = models.CharField(max_length=11, default="", choices=TypeChoices.choices)
    student_response = models.CharField(max_length=255, blank=True, null=True)
    correct_responses = models.JSONField(default=lambda: [])
    result = models.CharField(max_length=255, blank=True, null=True)
    weighting = models.FloatField(blank=True, null=True)
    latency = models.DurationField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now=True)
    description = models.CharField(max_length=255)
