from utils.step_utils import create_step

def strobe_new(channels, bpm, speed, color):
    pass

def strobe(start_step, channels, speed="fast"):
    """
    Creates a strobe effect for blinder lights
    """
    speeds = {
        "fast": {"steps": 4, "hold": 0},
        "medium": {"steps": 8, "hold": 1},
        "slow": {"steps": 12, "hold": 2}
    }

    config = speeds.get(speed, speeds["medium"])
    steps = []

    for i in range(config["steps"]):
        value = "255" if i % 2 == 0 else "0"
        values = ",".join([f"{channel}:{value}:0" for channel in channels])

        step = create_step(
            number=start_step + i,
            fade_in=0,
            hold=config["hold"],
            fade_out=0,
            values=values
        )
        steps.append(step)

    return steps
