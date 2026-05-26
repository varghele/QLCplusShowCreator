"""Cross-platform helpers for OpenGL state that ModernGL 5.11.x doesn't expose.

In moderngl 5.11 ``Context.depth_mask`` is NOT a property — assigning
``ctx.depth_mask = False`` silently stores it as an instance attribute and
never calls ``glDepthMask``. The renderer's beam / floor-projection passes
rely on disabling depth writes so they don't occlude later chassis draws,
so we reach past moderngl and call ``glDepthMask`` directly via ctypes.

The OpenGL function operates on whatever context is current on this
thread — moderngl makes its context current when it renders, so calling
this between ``vao.render(...)`` invocations from the same thread
correctly affects the moderngl-owned context.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import platform
from typing import Optional


_DEPTH_MASK_FN: Optional[ctypes._CFuncPtr] = None


def _load_gl_lib() -> ctypes.CDLL:
    system = platform.system()
    if system == 'Windows':
        # stdcall on win32
        return ctypes.windll.opengl32  # type: ignore[attr-defined]
    if system == 'Darwin':
        return ctypes.cdll.LoadLibrary(
            '/System/Library/Frameworks/OpenGL.framework/OpenGL'
        )
    # Linux / BSD
    name = ctypes.util.find_library('GL') or 'libGL.so.1'
    return ctypes.cdll.LoadLibrary(name)


def _resolve_gl_depth_mask() -> ctypes._CFuncPtr:
    global _DEPTH_MASK_FN
    if _DEPTH_MASK_FN is not None:
        return _DEPTH_MASK_FN
    lib = _load_gl_lib()
    fn = lib.glDepthMask
    fn.argtypes = [ctypes.c_ubyte]
    fn.restype = None
    _DEPTH_MASK_FN = fn
    return fn


def set_depth_mask(enabled: bool) -> None:
    """Enable (``True``) or disable (``False``) writes to the depth buffer.

    Replaces the no-op ``ctx.depth_mask = X`` assignment from moderngl
    5.11.x. Must be called with a current OpenGL context.
    """
    try:
        fn = _resolve_gl_depth_mask()
    except OSError:  # pragma: no cover — environment can't load libGL
        return
    fn(1 if enabled else 0)
