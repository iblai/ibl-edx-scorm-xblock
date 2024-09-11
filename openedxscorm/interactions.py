from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from django.utils.dateparse import parse_duration
from opaque_keys.edx.keys import UsageKey

from .models import ScormInteraction, ScormState

log = logging.getLogger(__name__)


def update_or_create_scorm_data(
    user_id: int, usage_key: UsageKey, events: list[dict[str, Any]]
) -> None:
    """Update or create all scorm state in the db"""
    interaction_events, sco_events = split_out_interactions(events)
    scorm_state = update_or_create_scorm_state(user_id, usage_key, sco_events)
    update_or_create_interaction(interaction_events, scorm_state)


def split_out_interactions(
    data: list[dict[str, Any]],
) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Return tuple of interactions and non-interaction events

    interaction events are a dict of their interaction index and the events
    """
    interactions = defaultdict(list)
    sco_events = []
    for event in data:
        if event["name"].startswith("cmi.interactions"):
            index = _get_interaction_index(event["name"])
            # We should only ever see cmi.interactions.N.*, but just in case, handle it
            if index is None:
                continue

            interactions[index].append(event)
        else:
            sco_events.append(event)

    return interactions, sco_events


def _get_interaction_index(name: str) -> int | None:
    """Return the index of the interaction from the event name or None if not found"""
    try:
        return int(name.split(".")[2])
    except (ValueError, IndexError):
        return None


def update_or_create_scorm_state(
    user_id: int, usage_key: UsageKey, events: list[dict[str, Any]]
) -> ScormState:
    query = {
        "user_id": user_id,
        "course_key": usage_key.course_key,
        "block_id": str(usage_key),
    }

    new_values = {}
    score_min = None
    score_max = None
    score_raw = None
    score_scaled = None
    session_times = []
    for event in events:
        name = event["name"]
        value = event["value"]

        # Scorm 1.1/1.2 only have lesson_status
        if name == "cmi.core.lesson_status":
            lesson_status = value
            if lesson_status in ["passed", "failed"]:
                new_values["success_status"] = lesson_status
            elif lesson_status in ["completed", "incomplete"]:
                new_values["completion_status"] = lesson_status
        # Scorm 2004 use success_status and completion_status
        elif name == "cmi.success_status":
            new_values["success_status"] = value
        elif name == "cmi.completion_status":
            new_values["completion_status"] = value
        elif name == "cmi.score.scaled":
            score_scaled = value
        elif name == ["cmi.score.min", "cmi.core.score.min"]:
            score_min = value
        elif name == ["cmi.score.max", "cmi.core.score.max"]:
            score_max = value
        elif name == ["cmi.score.raw", "cmi.core.score.raw"]:
            score_raw = value
        elif name in ["cmi.session_time", "cmi.core.session_time"]:
            session_sec = get_session_seconds(name, value)
            if session_sec is not None:
                session_times.append(session_sec)

    lesson_score = get_lesson_score(score_scaled, score_raw, score_min, score_max)
    if lesson_score is not None:
        new_values["lesson_score"] = lesson_score

    query["defaults"] = new_values
    log.debug("ScormState.update_or_create: %s", query)
    scorm_state, created = ScormState.objects.update_or_create(**query)
    if created:
        log.info("Created ScormState for %s, %s", user_id, usage_key)
    
    if session_times:
        scorm_state.session_times.extend(session_times)
        scorm_state.save()

    return scorm_state


def get_lesson_score(
    score_scaled: float | None,
    score_raw: float | None,
    score_min: float | None,
    score_max: float | None,
) -> float | None:
    """Return score based on how it was returned by the SCO"""
    if score_scaled is not None:
        return score_scaled
    elif score_raw is not None and score_min is not None and score_max is not None:
        return score_raw / (score_max - score_min)
    return None


def get_session_seconds(name:str, value: str | float) -> float | None:
    """Return the session time in seconds or None if not found"""
    # Scorm 1.1/1.2
    if name == "cmi.core.session_time":
        duration = parse_duration(value)
        return None if duration is None else duration.total_seconds()
    # Scorm 2004
    elif name == "cmi.session_time":
        return float(value)
    else:
        return None


def update_or_create_interaction(
    interactions: dict[int, list[dict[str, Any]]], scorm_state: ScormState
) -> None:
    for index, events in interactions.items():
        query = {"scorm_state": scorm_state, "index": index}
        prefix = f"cmi.interactions.{index}"

        new_values = {
            "correct_responses": get_correct_response_patterns(prefix, events)
        }
        for event in events:
            name = event["name"]
            value = event["value"]

            if name == f"{prefix}.id":
                query["interaction_id"] = value
            elif name == f"{prefix}.student_response":
                new_values["student_response"] = value
            elif name == f"{prefix}.type":
                new_values["type"] = value
            elif name == f"{prefix}.result":
                new_values["result"] = value
            elif name == f"{prefix}.weighting":
                new_values["weighting"] = value
            elif name == f"{prefix}.latency" and event.get("value") is not None:
                new_values["latency"] = parse_duration(value)
                if new_values["latency"] is None:
                    log.warning("Invalid Duration: %s", value)

        query["defaults"] = new_values
        log.debug("ScormInteraction.update_or_create: %s", query)
        _, created = ScormInteraction.objects.update_or_create(**query)
        if created:
            log.info(
                "Created ScormInteraction index=%s, id=%s for ScormState: %s",
                query["index"],
                query["interaction_id"],
                scorm_state,
            )


def get_correct_response_patterns(
    prefix: str, events: list[dict[str, Any]]
) -> list[str]:
    """Returns correct responses indexed the same as pattern index"""
    correct_indexes = []
    response_pattern_map = {}
    for event in events:
        for name, value in event.items():
            if name.startswith(f"{prefix}.correct_responses"):
                index = int(name.split(".")[3])
                response_pattern_map[index] = value

    correct_indexes = sorted(correct_indexes)
    return [response_pattern_map[idx] for idx in correct_indexes]
