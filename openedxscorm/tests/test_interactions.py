import logging
from collections import defaultdict
from unittest.mock import patch

import pytest
from common.djangoapps.student.tests.factories import UserFactory
from opaque_keys.edx.keys import UsageKey

from openedxscorm.interactions import (
    can_record_analytics,
    get_correct_response_patterns,
    get_lesson_score,
    split_out_interactions,
    update_or_create_interaction,
    update_or_create_scorm_state,
)
from openedxscorm.models import ScormInteraction, ScormState

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
    @pytest.mark.parametrize(
        "status, success, completion",
        (("completed", "unknown", "completed"), ("failed", "failed", "unknown")),
    )
    def test_create_new_state_1p2(self, status, success, completion):
        """
        Test that a new ScormState is created when none exists for the given user and usage_key.

        Tests Scorm 1.2
        """
        user = UserFactory()
        user_id = user.id
        usage_key = UsageKey.from_string(
            "block-v1:TestX+T101+2024_T1+type@scorm+block@block123"
        )
        events = [
            {"name": "cmi.core.lesson_status", "value": status},
            {"name": "cmi.score.scaled", "value": "0.5"},
            {"name": "cmi.core.session_time", "value": "PT1H0M0S"},  # 1 hour session
        ]

        # Act: Call the function to create a new ScormState
        scorm_state = update_or_create_scorm_state(user_id, usage_key, events)

        # Assert: Ensure the ScormState was created with correct fields
        assert scorm_state.user_id == user_id
        assert scorm_state.course_key == usage_key.course_key
        assert scorm_state.usage_key == usage_key
        assert scorm_state.completion_status == completion
        assert scorm_state.success_status == success
        assert scorm_state.lesson_score == 0.5
        assert scorm_state.session_times == [3600]  # 1 hour in seconds
        assert ScormState.objects.count() == 1

    def test_create_new_state_2004(self):
        """
        Test that a new ScormState is created when none exists for the given user and usage_key.

        Tests Scorm 2004
        """
        user = UserFactory()
        user_id = user.id
        usage_key = UsageKey.from_string(
            "block-v1:TestX+T101+2024_T1+type@scorm+block@block123"
        )
        events = [
            {
                "name": "cmi.success_status",
                "value": ScormState.SuccessChoices.PASSED,
            },
            {
                "name": "cmi.completion_status",
                "value": ScormState.CompleteChoices.COMPLETED,
            },
        ]

        # Act: Call the function to create a new ScormState
        scorm_state = update_or_create_scorm_state(user_id, usage_key, events)

        # Assert: Ensure the ScormState was created with correct fields
        assert scorm_state.user_id == user_id
        assert scorm_state.course_key == usage_key.course_key
        assert scorm_state.usage_key == usage_key
        assert scorm_state.success_status == ScormState.SuccessChoices.PASSED
        assert scorm_state.completion_status == ScormState.CompleteChoices.COMPLETED
        assert scorm_state.lesson_score is None
        assert scorm_state.session_times == []
        assert ScormState.objects.count() == 1

    def test_scorm_state_created_for_multiple_users(self):
        """
        Test scorm state can be created for multiple users for same blocks
        """
        user1 = UserFactory()
        user2 = UserFactory()
        user1_id = user1.id
        user2_id = user2.id
        usage_key = UsageKey.from_string(
            "block-v1:TestX+T101+2024_T1+type@scorm+block@block123"
        )
        events = [
            {"name": "cmi.core.lesson_status", "value": "completed"},
            {"name": "cmi.score.scaled", "value": "0.5"},
            {"name": "cmi.core.session_time", "value": "PT1H0M0S"},  # 1 hour session
        ]

        # Act: Call the function to create a new ScormState
        scorm_state1 = update_or_create_scorm_state(user1_id, usage_key, events)
        scorm_state2 = update_or_create_scorm_state(user2_id, usage_key, events)

        # Assert: Ensure the ScormState was created with correct fields
        for scorm_state in [scorm_state1, scorm_state2]:
            assert scorm_state.course_key == usage_key.course_key
            assert scorm_state.usage_key == usage_key
            assert scorm_state.completion_status == "completed"
            assert scorm_state.lesson_score == 0.5
            assert scorm_state.session_times == [3600]  # 1 hour in seconds
        assert ScormState.objects.count() == 2

    def test_update_existing_state(self):
        """
        Test that an existing ScormState is updated when one exists for the user and usage_key.
        """

        # Pre-create a ScormState in the databese
        scorm_state = factories.ScormStateFactory(
            success_status=ScormState.SuccessChoices.FAILED,
            completion_status=ScormState.CompleteChoices.COMPLETED,
            lesson_score=0.25,
            session_times=[600],  # 10 minutes in seconds
        )
        # other existing scorm state that won't be updated
        other = factories.ScormStateFactory(
            course_key=scorm_state.course_key,
            usage_key=scorm_state.usage_key,
            lesson_score=1,
            session_times=[],
        )
        user_id = scorm_state.user.id
        usage_key = scorm_state.usage_key

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
        assert ScormState.objects.count() == 2
        other.refresh_from_db()
        assert other.lesson_score == 1
        assert other.success_status == ScormState.SuccessChoices.UNKNOWN
        assert not other.session_times

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
            {
                "name": "cmi.core.lesson_status",
                "value": ScormState.CompleteChoices.COMPLETED,
            },
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
        assert scorm_state.completion_status == ScormState.CompleteChoices.COMPLETED
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


@pytest.mark.django_db
class TestUpdateOrCreateInteraction:
    def test_create_interaction(self):
        """Test that a new interaction is created successfully in the database."""
        scorm_state = factories.ScormStateFactory()
        interactions = {
            0: [
                {"name": "cmi.interactions.0.id", "value": "interaction_1"},
                {"name": "cmi.interactions.0.student_response", "value": "response_1"},
                {"name": "cmi.interactions.0.type", "value": "true-false"},
                {"name": "cmi.interactions.0.result", "value": "correct"},
                {"name": "cmi.interactions.0.weighting", "value": "1.0"},
            ]
        }

        update_or_create_interaction(interactions, scorm_state)

        interaction = ScormInteraction.objects.get(scorm_state=scorm_state, index=0)
        assert interaction.interaction_id == "interaction_1"
        assert interaction.student_response == "response_1"
        assert interaction.type == ScormInteraction.TypeChoices.TRUE_FALSE
        assert interaction.result == "correct"
        assert interaction.weighting == 1.0

    def test_update_existing_interaction(self):
        """Test that an existing interaction is updated in the database."""
        scorm_state = factories.ScormStateFactory()
        interaction = ScormInteraction.objects.create(
            scorm_state=scorm_state, index=0, interaction_id="interaction_1"
        )
        interactions = {
            0: [
                {"name": "cmi.interactions.0.id", "value": "interaction_1"},
                {
                    "name": "cmi.interactions.0.student_response",
                    "value": "updated_response",
                },
                {"name": "cmi.interactions.0.type", "value": "choice"},
                {"name": "cmi.interactions.0.result", "value": "incorrect"},
            ]
        }

        update_or_create_interaction(interactions, scorm_state)

        interaction.refresh_from_db()
        assert interaction.student_response == "updated_response"
        assert interaction.type == "choice"
        assert interaction.result == "incorrect"

    def test_invalid_latency(self, caplog):
        """Test that an invalid latency value is logged as a warning."""
        scorm_state = factories.ScormStateFactory()
        interactions = {
            0: [{"name": "cmi.interactions.0.latency", "value": "invalid_duration"}]
        }

        with caplog.at_level(logging.WARNING):
            update_or_create_interaction(interactions, scorm_state)

        assert "Invalid Latency" in caplog.text
        interaction = ScormInteraction.objects.get(scorm_state=scorm_state, index=0)
        assert interaction.latency is None


class TestGetLessonScore:
    def test_with_scaled_score(self):
        """Test case where score_scaled is provided."""
        score = get_lesson_score(
            score_scaled=0.8, score_raw=None, score_min=None, score_max=None
        )
        assert score == 0.8

    def test_with_raw_min_max(self):
        """Test case where score_raw, score_min, and score_max are provided."""
        score = get_lesson_score(
            score_scaled=None, score_raw=80, score_min=0, score_max=100
        )
        assert score == 0.8

    @pytest.mark.parametrize("param", ("score_raw", "score_min", "score_max"))
    def test_with_missing_min_max(self, param):
        """Test case where one of score_raw, min, max is None"""
        kwargs = {
            "score_scaled": None,
            "score_raw": 80,
            "score_min": 0,
            "score_max": 100,
        }
        kwargs[param] = None
        score = get_lesson_score(**kwargs)
        assert score is None

    def test_with_no_values(self):
        """Test case where no scores are provided."""
        score = get_lesson_score(
            score_scaled=None, score_raw=None, score_min=None, score_max=None
        )
        assert score is None


class TestGetCorrectResponsePatterns:
    def test_single_correct_response(self):
        """Test correct response pattern extraction with a single correct response."""
        events = [
            {"cmi.interactions.0.correct_responses.0.pattern": "response_1"},
        ]
        correct_responses = get_correct_response_patterns("cmi.interactions.0", events)
        assert correct_responses == ["response_1"]

    def test_multiple_correct_responses(self):
        """Test correct response pattern extraction with multiple responses in the correct order."""
        events = [
            {"cmi.interactions.0.correct_responses.0.pattern": "response_1"},
            {"cmi.interactions.0.correct_responses.1.pattern": "response_2"},
        ]
        correct_responses = get_correct_response_patterns("cmi.interactions.0", events)
        assert correct_responses == ["response_1", "response_2"]

    def test_unordered_correct_responses(self):
        """Test correct response patterns when responses are provided out of order."""
        events = [
            {"cmi.interactions.0.correct_responses.1.pattern": "response_2"},
            {"cmi.interactions.0.correct_responses.0.pattern": "response_1"},
        ]
        correct_responses = get_correct_response_patterns("cmi.interactions.0", events)
        assert correct_responses == ["response_1", "response_2"]

    def test_no_correct_responses(self):
        """Test when no correct responses are found in the events."""
        events = [{"cmi.interactions.0.student_response": "student_response_value"}]
        correct_responses = get_correct_response_patterns("cmi.interactions.0", events)
        assert correct_responses == []
