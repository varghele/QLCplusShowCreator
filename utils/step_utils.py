import xml.etree.ElementTree as ET


def create_step(number, fade_in=0, hold=0, fade_out=0, values=None):
    """Base function for creating steps"""
    step = ET.Element("Step")
    step.set("Number", str(number))
    step.set("FadeIn", str(fade_in))
    step.set("Hold", str(hold))
    step.set("FadeOut", str(fade_out))
    step.set("Values", "17")

    if values:
        step.text = values

    return step
