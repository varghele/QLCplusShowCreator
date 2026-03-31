import math
from typing import Dict, Callable

from effects.types import MovementContext, MovementResult


def static(ctx: MovementContext) -> MovementResult:
    """Fixed pan/tilt position."""
    return MovementResult(pan=ctx.center_pan, tilt=ctx.center_tilt)


def circle(ctx: MovementContext) -> MovementResult:
    """Circular sweep."""
    pan = ctx.center_pan + ctx.pan_amplitude * math.cos(ctx.t)
    tilt = ctx.center_tilt + ctx.tilt_amplitude * math.sin(ctx.t)
    return MovementResult(pan=pan, tilt=tilt)


def _polygon_phase(ctx: MovementContext, num_corners: int):
    """Compute phase for polygon shapes, applying phase offset if enabled."""
    phase = ctx.progress * num_corners * ctx.total_cycles
    if ctx.phase_offset_enabled and ctx.total_fixtures > 1:
        phase_offset_cycles = (ctx.fixture_index * ctx.phase_offset_degrees / 360.0) * num_corners
        phase = phase + phase_offset_cycles
    return phase


def diamond(ctx: MovementContext) -> MovementResult:
    """4-corner diamond path."""
    phase = _polygon_phase(ctx, 4)
    corner = int(phase) % 4
    local_t = phase - int(phase)
    corners = [
        (ctx.center_pan, ctx.center_tilt - ctx.tilt_amplitude),
        (ctx.center_pan + ctx.pan_amplitude, ctx.center_tilt),
        (ctx.center_pan, ctx.center_tilt + ctx.tilt_amplitude),
        (ctx.center_pan - ctx.pan_amplitude, ctx.center_tilt),
    ]
    start = corners[corner]
    end = corners[(corner + 1) % 4]
    pan = start[0] + local_t * (end[0] - start[0])
    tilt = start[1] + local_t * (end[1] - start[1])
    return MovementResult(pan=pan, tilt=tilt)


def square(ctx: MovementContext) -> MovementResult:
    """4-corner square path."""
    phase = _polygon_phase(ctx, 4)
    corner = int(phase) % 4
    local_t = phase - int(phase)
    corners = [
        (ctx.center_pan - ctx.pan_amplitude, ctx.center_tilt - ctx.tilt_amplitude),
        (ctx.center_pan + ctx.pan_amplitude, ctx.center_tilt - ctx.tilt_amplitude),
        (ctx.center_pan + ctx.pan_amplitude, ctx.center_tilt + ctx.tilt_amplitude),
        (ctx.center_pan - ctx.pan_amplitude, ctx.center_tilt + ctx.tilt_amplitude),
    ]
    start = corners[corner]
    end = corners[(corner + 1) % 4]
    pan = start[0] + local_t * (end[0] - start[0])
    tilt = start[1] + local_t * (end[1] - start[1])
    return MovementResult(pan=pan, tilt=tilt)


def triangle(ctx: MovementContext) -> MovementResult:
    """3-corner triangular path."""
    phase = _polygon_phase(ctx, 3)
    corner = int(phase) % 3
    local_t = phase - int(phase)
    corners = [
        (ctx.center_pan, ctx.center_tilt - ctx.tilt_amplitude),
        (ctx.center_pan + ctx.pan_amplitude * 0.866, ctx.center_tilt + ctx.tilt_amplitude * 0.5),
        (ctx.center_pan - ctx.pan_amplitude * 0.866, ctx.center_tilt + ctx.tilt_amplitude * 0.5),
    ]
    start = corners[corner]
    end = corners[(corner + 1) % 3]
    pan = start[0] + local_t * (end[0] - start[0])
    tilt = start[1] + local_t * (end[1] - start[1])
    return MovementResult(pan=pan, tilt=tilt)


def figure_8(ctx: MovementContext) -> MovementResult:
    """Figure-eight pattern."""
    pan = ctx.center_pan + ctx.pan_amplitude * math.sin(ctx.t)
    tilt = ctx.center_tilt + ctx.tilt_amplitude * math.sin(2 * ctx.t)
    return MovementResult(pan=pan, tilt=tilt)


def lissajous(ctx: MovementContext) -> MovementResult:
    """Configurable frequency ratio pattern."""
    ratio_parts = ctx.lissajous_ratio.split(':')
    try:
        freq_pan = int(ratio_parts[0])
        freq_tilt = int(ratio_parts[1])
    except (ValueError, IndexError):
        freq_pan, freq_tilt = 1, 2
    pan = ctx.center_pan + ctx.pan_amplitude * math.sin(freq_pan * ctx.t)
    tilt = ctx.center_tilt + ctx.tilt_amplitude * math.sin(freq_tilt * ctx.t)
    return MovementResult(pan=pan, tilt=tilt)


def random_movement(ctx: MovementContext) -> MovementResult:
    """Pseudo-random smooth motion using multiple sine waves."""
    pan = ctx.center_pan + ctx.pan_amplitude * (
        0.5 * math.sin(3 * ctx.t) + 0.3 * math.sin(7 * ctx.t) + 0.2 * math.sin(11 * ctx.t)
    )
    tilt = ctx.center_tilt + ctx.tilt_amplitude * (
        0.5 * math.sin(5 * ctx.t) + 0.3 * math.sin(11 * ctx.t) + 0.2 * math.sin(13 * ctx.t)
    )
    return MovementResult(pan=pan, tilt=tilt)


def bounce(ctx: MovementContext) -> MovementResult:
    """Bouncing pattern using triangle waves."""
    bounce_t = ctx.progress * 4 * ctx.total_cycles
    if ctx.phase_offset_enabled and ctx.total_fixtures > 1:
        phase_offset_cycles = (ctx.fixture_index * ctx.phase_offset_degrees / 360.0) * 4
        bounce_t = bounce_t + phase_offset_cycles
    pan_t = abs((bounce_t % 2) - 1)
    tilt_t = abs(((bounce_t + 0.5) % 2) - 1)
    pan = ctx.center_pan - ctx.pan_amplitude + 2 * ctx.pan_amplitude * pan_t
    tilt = ctx.center_tilt - ctx.tilt_amplitude + 2 * ctx.tilt_amplitude * tilt_t
    return MovementResult(pan=pan, tilt=tilt)


MOVEMENT_REGISTRY: Dict[str, Callable[[MovementContext], MovementResult]] = {
    "static": static,
    "circle": circle,
    "diamond": diamond,
    "square": square,
    "triangle": triangle,
    "figure_8": figure_8,
    "lissajous": lissajous,
    "random": random_movement,
    "bounce": bounce,
}
