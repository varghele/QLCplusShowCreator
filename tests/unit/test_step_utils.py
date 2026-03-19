# tests/unit/test_step_utils.py
"""Unit tests for utils/step_utils.py - XML step element creation."""

import xml.etree.ElementTree as ET

from utils.step_utils import create_step


class TestCreateStep:

    def test_returns_element(self):
        step = create_step(0)
        assert isinstance(step, ET.Element)
        assert step.tag == "Step"

    def test_default_attributes(self):
        step = create_step(1)
        assert step.get("Number") == "1"
        assert step.get("FadeIn") == "0"
        assert step.get("Hold") == "0"
        assert step.get("FadeOut") == "0"
        assert step.get("Values") == "0"

    def test_custom_fade_hold(self):
        step = create_step(5, fade_in=100, hold=500, fade_out=200)
        assert step.get("Number") == "5"
        assert step.get("FadeIn") == "100"
        assert step.get("Hold") == "500"
        assert step.get("FadeOut") == "200"

    def test_no_values_text_is_none(self):
        step = create_step(0)
        assert step.text is None

    def test_values_set_as_text(self):
        step = create_step(0, values="0,255,128,64")
        assert step.text == "0,255,128,64"

    def test_values_attribute_always_zero(self):
        """The Values attribute is always 0, regardless of the text content."""
        step = create_step(0, values="some data")
        assert step.get("Values") == "0"
        assert step.text == "some data"

    def test_number_is_string(self):
        step = create_step(42)
        assert step.get("Number") == "42"
