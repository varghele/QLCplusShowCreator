# visualizer/renderer/engine.py
# ModernGL render engine with PyQt6 integration

import time
import moderngl
from typing import Optional

from PyQt6.QtWidgets import QWidget
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QSurfaceFormat

from .camera import OrbitCamera
from .stage import StageRenderer
from .gizmo import CoordinateGizmo


class RenderEngine(QOpenGLWidget):
    """
    ModernGL-based 3D render engine for PyQt6.

    Provides:
    - OpenGL context management
    - Orbit camera with mouse controls
    - Stage floor with grid
    - FPS counter
    - Window resize handling
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize render engine."""
        # Set OpenGL format before creating widget
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setDepthBufferSize(24)
        fmt.setSamples(4)  # MSAA
        QSurfaceFormat.setDefaultFormat(fmt)

        super().__init__(parent)

        # ModernGL context (created in initializeGL)
        self.ctx: Optional[moderngl.Context] = None

        # Camera
        self.camera = OrbitCamera()

        # Renderers (created in initializeGL)
        self.stage_renderer: Optional[StageRenderer] = None
        self.gizmo_renderer: Optional[CoordinateGizmo] = None

        # Stage dimensions
        self.stage_width = 10.0
        self.stage_height = 6.0  # depth

        # Mouse tracking
        self.setMouseTracking(True)
        self.last_mouse_pos = None
        self.mouse_button = None

        # FPS counter
        self.fps = 0.0
        self.frame_count = 0
        self.fps_time = time.time()
        self.last_frame_time = time.time()
        self._first_frame = True  # Debug flag

        # Render timer (60 FPS target)
        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self.update)
        self.render_timer.start(16)  # ~60 FPS

        # Enable keyboard focus
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def initializeGL(self):
        """Initialize OpenGL context and resources."""
        try:
            # Create ModernGL context from existing OpenGL context
            # standalone=False tells ModernGL to use the existing Qt context
            self.ctx = moderngl.create_context(standalone=False)

            # Get Qt's framebuffer object ID for rendering
            # QOpenGLWidget uses an FBO, not the default framebuffer
            self.qt_fbo_id = self.defaultFramebufferObject()
            print(f"Qt FBO ID: {self.qt_fbo_id}")

            # Enable depth testing
            self.ctx.enable(moderngl.DEPTH_TEST)

            # Enable blending for transparency
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

            # Create stage renderer
            self.stage_renderer = StageRenderer(
                self.ctx,
                self.stage_width,
                self.stage_height
            )

            # Create coordinate gizmo
            self.gizmo_renderer = CoordinateGizmo(self.ctx)

            # Set camera to fit stage
            self.camera.set_stage_size(self.stage_width, self.stage_height)

            print(f"OpenGL initialized: {self.ctx.info['GL_RENDERER']}")
            print(f"  Stage size: {self.stage_width}m x {self.stage_height}m")
            print(f"  Camera distance: {self.camera.distance}")
            print(f"  Camera position: {self.camera.get_position()}")

        except Exception as e:
            print(f"Failed to initialize OpenGL: {e}")
            import traceback
            traceback.print_exc()

    def resizeGL(self, width: int, height: int):
        """Handle window resize."""
        # Update camera aspect ratio
        if height > 0:
            self.camera.set_aspect(width / height)

        # Note: Viewport is set per-frame when binding the FBO

    def paintGL(self):
        """Render frame."""
        if not self.ctx:
            return

        # Debug: first frame info
        if self._first_frame:
            print(f"First frame rendering...")
            print(f"  Viewport: {self.ctx.viewport}")
            print(f"  Stage renderer: {self.stage_renderer is not None}")
            # Check for OpenGL errors
            try:
                error = self.ctx.error
                if error:
                    print(f"  OpenGL error: {error}")
            except:
                pass
            self._first_frame = False

        # Calculate FPS
        self._update_fps()

        # IMPORTANT: Bind Qt's FBO before rendering
        # QOpenGLWidget uses an FBO, not the default framebuffer (0)
        # We need to get the current FBO ID as it may change on resize
        qt_fbo_id = self.defaultFramebufferObject()
        self.ctx.fbo = self.ctx.detect_framebuffer(qt_fbo_id)
        self.ctx.fbo.use()

        # Set viewport to widget size
        self.ctx.viewport = (0, 0, self.width(), self.height())

        # Clear screen (dark background)
        self.ctx.fbo.clear(0.05, 0.05, 0.08, 1.0)

        # Get view-projection matrix
        mvp = self.camera.get_view_projection_matrix()

        # Render stage
        if self.stage_renderer:
            self.stage_renderer.render(mvp)

        # TODO: Phase V5 - Render fixtures
        # TODO: Phase V6 - Render beams

        # Render coordinate gizmo (always on top, in corner)
        if self.gizmo_renderer:
            view_matrix = self.camera.get_view_matrix()
            self.gizmo_renderer.render(view_matrix, self.width(), self.height())

    def _update_fps(self):
        """Update FPS counter."""
        self.frame_count += 1
        current_time = time.time()

        # Update FPS every second
        elapsed = current_time - self.fps_time
        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.frame_count = 0
            self.fps_time = current_time

        self.last_frame_time = current_time

    def get_fps(self) -> float:
        """Get current FPS."""
        return self.fps

    def set_stage_size(self, width: float, height: float):
        """
        Update stage dimensions.

        Args:
            width: Stage width in meters
            height: Stage depth in meters
        """
        print(f"RenderEngine: Updating stage size to {width}x{height}m")
        self.stage_width = width
        self.stage_height = height

        if self.stage_renderer:
            # Make sure we're in the right OpenGL context
            self.makeCurrent()
            self.stage_renderer.set_size(width, height)
            self.doneCurrent()

        self.camera.set_stage_size(width, height)
        print(f"RenderEngine: Stage size update complete")

    def set_grid_size(self, grid_size: float):
        """
        Update grid spacing.

        Args:
            grid_size: Grid spacing in meters
        """
        if self.stage_renderer:
            # Make sure we're in the right OpenGL context
            self.makeCurrent()
            self.stage_renderer.set_grid_size(grid_size)
            self.doneCurrent()
            print(f"RenderEngine: Grid size updated to {grid_size}m")

    def reset_camera(self):
        """Reset camera to default position."""
        self.camera.reset()

    # --- Mouse Event Handlers ---

    def mousePressEvent(self, event):
        """Handle mouse button press."""
        self.last_mouse_pos = event.position()
        self.mouse_button = event.button()

    def mouseReleaseEvent(self, event):
        """Handle mouse button release."""
        self.last_mouse_pos = None
        self.mouse_button = None

    def mouseMoveEvent(self, event):
        """Handle mouse movement."""
        if self.last_mouse_pos is None:
            return

        pos = event.position()
        delta_x = pos.x() - self.last_mouse_pos.x()
        delta_y = pos.y() - self.last_mouse_pos.y()

        if self.mouse_button == Qt.MouseButton.LeftButton:
            # Orbit camera
            self.camera.orbit(delta_x, delta_y)

        elif self.mouse_button == Qt.MouseButton.RightButton:
            # Pan camera
            self.camera.pan(delta_x, delta_y)

        elif self.mouse_button == Qt.MouseButton.MiddleButton:
            # Also pan with middle button
            self.camera.pan(delta_x, delta_y)

        self.last_mouse_pos = pos

    def wheelEvent(self, event):
        """Handle mouse wheel scroll."""
        delta = event.angleDelta().y() / 120.0  # Normalize to +/- 1
        self.camera.zoom(delta)

    def keyPressEvent(self, event):
        """Handle key press."""
        if event.key() == Qt.Key.Key_Home:
            self.reset_camera()
        elif event.key() == Qt.Key.Key_R:
            self.reset_camera()

    # --- Cleanup ---

    def cleanup(self):
        """Release GPU resources."""
        if self.render_timer:
            self.render_timer.stop()

        if self.stage_renderer:
            self.stage_renderer.release()
            self.stage_renderer = None

        if self.gizmo_renderer:
            self.gizmo_renderer.release()
            self.gizmo_renderer = None

        if self.ctx:
            self.ctx.release()
            self.ctx = None

    def closeEvent(self, event):
        """Handle widget close."""
        self.cleanup()
        super().closeEvent(event)
