from collections import defaultdict
from unittest.mock import patch

import pytest
from common.djangoapps.student.tests.factories import UserFactory
from opaque_keys.edx.keys import UsageKey

from openedxscorm.interactions import (
    can_record_analytics,
    get_lesson_score,
    split_out_interactions,
    update_or_create_scorm_state,
)
from openedxscorm.models import ScormState

from . import factories


@pytest.fixture
def mock_in_preview_mode():
    with patch("openedxscorm.interactions.in_preview_mode") as mock_preview_mode:
        yield mock_preview_mode


def test_can_record_analytics_cms(settings, mock_in_preview_mode):
    """
    Test can_record_analytics returns False if the service variant is 'cms'.
    """
    settings.SERVICE_VARIANT = "cms"
    assert not can_record_analytics()
    mock_in_preview_mode.assert_not_called()


def test_can_record_analytics_in_preview(settings, mock_in_preview_mode):
    """
    Test can_record_analytics returns False if in preview mode.
    """
    settings.SERVICE_VARIANT = "lms"
    mock_in_preview_mode.return_value = True
    assert not can_record_analytics()
    mock_in_preview_mode.assert_called_once()


def test_can_record_analytics_normal(settings, mock_in_preview_mode):
    """
    Test can_record_analytics returns True if not in preview mode and in LMS.
    """
    settings.SERVICE_VARIANT = "lms"
    mock_in_preview_mode.return_value = False
    assert can_record_analytics()
    mock_in_preview_mode.assert_called_once()


def test_split_out_interactions():
    """
    Test split_out_interactions returns correctly split interaction and sco events.
    """
    data = [
        {"name": "cmi.interactions.0.type", "value": "choice"},
        {"name": "cmi.core.lesson_status", "value": "completed"},
        {"name": "cmi.interactions.1.type", "value": "true-false"},
    ]

    interactions, sco_events = split_out_interactions(data)

    expected_interactions = {
        0: [data[0]],
        1: [data[2]],
    }
    expected_sco_events = [data[1]]

    assert interactions == expected_interactions
    assert sco_events == expected_sco_events


def test_split_out_interactions_no_interactions():
    """
    Test split_out_interactions when no interaction events are present.
    """
    data = [
        {"name": "cmi.core.lesson_status", "value": "completed"},
        {"name": "cmi.core.score.raw", "value": "85"},
    ]

    interactions, sco_events = split_out_interactions(data)

    assert interactions == defaultdict(list)
    assert sco_events == data


@pytest.mark.django_db
class TestUpdateOrCreateScormState:
    def test_create_new_state(self):
        """
        Test that a new ScormState is created when none exists for the given user and usage_key.
        """
        user = UserFactory()
        user_id = user.id
        usage_key = UsageKey.from_string(
            "block-v1:TestX+T101+2024_T1+type@scorm+block@block123"
        )
        events = [
            {"name": "cmi.core.lesson_status", "value": "completed"},
            {"name": "cmi.score.scaled", "value": "0.5"},
            {"name": "cmi.core.session_time", "value": "PT1H0M0S"},  # 1 hour session
        ]

        # Act: Call the function to create a new ScormState
        scorm_state = update_or_create_scorm_state(user_id, usage_key, events)

        # Assert: Ensure the ScormState was created with correct fields
        assert scorm_state.user_id == user_id
        assert scorm_state.course_key == usage_key.course_key
        assert scorm_state.usage_key == usage_key
        assert scorm_state.completion_status == "completed"
        assert scorm_state.lesson_score == 0.5
        assert scorm_state.session_times == [3600]  # 1 hour in seconds
        assert ScormState.objects.count() == 1

    def test_update_existing_state(self):
        """
        Test that an existing ScormState is updated when one exists for the user and usage_key.
        """
        user = UserFactory()
        user_id = user.id
        usage_key = UsageKey.from_string(
            "block-v1:TestX+T101+2024_T1+type@scorm+block@block123"
        )

        # Pre-create a ScormState in the databese
        scorm_state = factories.ScormStateFactory(
            user_id=user_id,
            course_key=usage_key.course_key,
            usage_key=usage_key,
            success_status=ScormState.SuccessChoices.FAILED,
            completion_status=ScormState.CompleteChoices.COMPLETED,
            lesson_score=0.25,
            session_times=[600],  # 10 minutes in seconds
        )

        # New events to update the existing ScormState
        events = [
            {"name": "cmi.success_status", "value": ScormState.SuccessChoices.PASSED},
            {"name": "cmi.score.scaled", "value": "0.5"},
            {
                "name": "cmi.core.session_time",
                "value": "PT0H30M0S",
            },  # 30-minute session
        ]

        # Act: Call the function to update the existing ScormState
        updated_scorm_state = update_or_create_scorm_state(user_id, usage_key, events)

        # Assert: Ensure the ScormState was updated correctly
        assert updated_scorm_state.user_id == user_id
        assert updated_scorm_state.course_key == usage_key.course_key
        assert updated_scorm_state.usage_key == usage_key
        assert updated_scorm_state.success_status == ScormState.SuccessChoices.PASSED
        assert updated_scorm_state.lesson_score == 0.5
        assert updated_scorm_state.session_times == [600, 1800]

    @pytest.mark.django_db
    def test_multiple_events(self):
        """
        Test handling of multiple score and session time events.
        """
        user = UserFactory()
        user_id = user.id
        usage_key = UsageKey.from_string(
            "block-v1:TestX+T102+2024_T2+type@scorm+block@block456"
        )

        events = [
            {"name": "cmi.core.lesson_status", "value": "completed"},
            {"name": "cmi.score.raw", "value": "75"},
            {"name": "cmi.score.min", "value": "50"},
            {"name": "cmi.score.max", "value": "100"},
            {
                "name": "cmi.core.session_time",
                "value": "PT0H45M0S",
            },  # 45 minutes session
            {
                "name": "cmi.core.session_time",
                "value": "PT0H15M0S",
            },  # 15 minutes session
        ]

        # Act: Call the function to create a new ScormState
        scorm_state = update_or_create_scorm_state(user_id, usage_key, events)

        # Assert: Ensure the ScormState was created with correct fields
        assert scorm_state.user_id == user_id
        assert scorm_state.course_key == usage_key.course_key
        assert scorm_state.usage_key == usage_key
        assert scorm_state.completion_status == "completed"
        assert scorm_state.lesson_score == 75 / (100 - 50)
        assert len(scorm_state.session_times) == 2  # Two session times
        assert scorm_state.session_times == [
            2700,
            900,
        ]  # 45 mins and 15 mins in seconds

    @pytest.mark.django_db
    def test_no_events(self):
        """
        Test that no ScormState is created if no relevant events are provided.
        """
        user = UserFactory()
        user_id = user.id
        usage_key = UsageKey.from_string(
            "block-v1:TestX+T103+2024_T3+type@scorm+block@block789"
        )

        # Empty events list
        events = []

        # Act: Call the function with no events
        scorm_state = update_or_create_scorm_state(user_id, usage_key, events)

        # Assert: Ensure the ScormState was still created but has no session times or scores
        assert scorm_state.user_id == user_id
        assert scorm_state.course_key == usage_key.course_key
        assert scorm_state.usage_key == usage_key
        assert scorm_state.lesson_score is None
        assert not scorm_state.session_times  # Should be empty list


class TestGetLessonScore:
    def test_with_scaled_score(self):
        """Test case where score_scaled is provided."""
        score = get_lesson_score(
            score_scaled="0.8", score_raw=None, score_min=None, score_max=None
        )
        assert score == 0.8

    def test_with_raw_min_max(self):
        """Test case where score_raw, score_min, and score_max are provided."""
        score = get_lesson_score(
            score_scaled=None, score_raw="80", score_min="0", score_max="100"
        )
        assert score == 0.8

    def test_with_missing_min_max(self):
        """Test case where score_raw is provided but score_min or score_max is missing."""
        score = get_lesson_score(
            score_scaled=None, score_raw="80", score_min="0", score_max=None
        )
        assert score is None

    def test_with_invalid_scaled_value(self):
        """Test case where score_scaled is an invalid (non-numeric) string."""
        score = get_lesson_score(
            score_scaled="invalid", score_raw=None, score_min=None, score_max=None
        )
        assert score is None

    def test_with_invalid_raw_value(self):
        """Test case where score_raw is an invalid (non-numeric) string."""
        score = get_lesson_score(
            score_scaled=None, score_raw="invalid", score_min="0", score_max="100"
        )
        assert score is None

    def test_with_invalid_min_max_values(self):
        """Test case where score_min or score_max are invalid (non-numeric) strings."""
        score = get_lesson_score(
            score_scaled=None, score_raw="80", score_min="invalid", score_max="100"
        )
        assert score is None

    def test_with_no_values(self):
        """Test case where no scores are provided."""
        score = get_lesson_score(
            score_scaled=None, score_raw=None, score_min=None, score_max=None
        )
        assert score is None
