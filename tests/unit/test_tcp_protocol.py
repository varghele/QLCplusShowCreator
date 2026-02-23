# tests/unit/test_tcp_protocol.py
"""Unit tests for utils/tcp/protocol.py - Visualizer protocol message creation."""

import json
import pytest
from utils.tcp.protocol import MessageType, _infer_gobo_pattern, GOBO_PATTERN_KEYWORDS


class TestMessageType:

    def test_values(self):
        assert MessageType.STAGE.value == "stage"
        assert MessageType.FIXTURES.value == "fixtures"
        assert MessageType.GROUPS.value == "groups"
        assert MessageType.UPDATE.value == "update"
        assert MessageType.HEARTBEAT.value == "heartbeat"
        assert MessageType.ACK.value == "ack"

    def test_all_members(self):
        expected = {"STAGE", "FIXTURES", "GROUPS", "UPDATE", "HEARTBEAT", "ACK"}
        assert set(m.name for m in MessageType) == expected


class TestInferGoboPattern:

    def test_open_pattern(self):
        assert _infer_gobo_pattern("Open") == 0
        assert _infer_gobo_pattern("No gobo") == 0
        assert _infer_gobo_pattern("White open") == 0

    def test_dot_circle(self):
        assert _infer_gobo_pattern("Circle dots") == 1
        assert _infer_gobo_pattern("Dot pattern") == 1

    def test_star(self):
        assert _infer_gobo_pattern("Star burst") == 2

    def test_lines(self):
        assert _infer_gobo_pattern("Line pattern") == 3
        assert _infer_gobo_pattern("Bar") == 3

    def test_triangle(self):
        assert _infer_gobo_pattern("Triangle") == 4

    def test_cross(self):
        assert _infer_gobo_pattern("Cross pattern") == 5

    def test_breakup(self):
        assert _infer_gobo_pattern("Breakup") == 6

    def test_numbered_gobo(self):
        # "Gobo 1" -> pattern 1, "Gobo 2" -> pattern 2, etc.
        assert _infer_gobo_pattern("Gobo 1") == 1
        assert _infer_gobo_pattern("Gobo 2") == 2
        assert _infer_gobo_pattern("Gobo 6") == 6
        # Gobo 7 wraps: ((7-1) % 6) + 1 = 1
        assert _infer_gobo_pattern("Gobo 7") == 1

    def test_unknown_defaults_to_6(self):
        assert _infer_gobo_pattern("SomethingUnknown") == 6

    def test_case_insensitive(self):
        assert _infer_gobo_pattern("STAR") == 2
        assert _infer_gobo_pattern("circle") == 1


class TestGoboPatternKeywords:

    def test_all_keywords_have_valid_pattern_ids(self):
        for keyword, pattern_id in GOBO_PATTERN_KEYWORDS.items():
            assert 0 <= pattern_id <= 6, f"Invalid pattern ID {pattern_id} for '{keyword}'"

    def test_open_keywords_map_to_zero(self):
        open_keywords = ['open', 'no gobo', 'white', 'clear']
        for kw in open_keywords:
            assert GOBO_PATTERN_KEYWORDS[kw] == 0