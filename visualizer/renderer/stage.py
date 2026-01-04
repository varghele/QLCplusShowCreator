# visualizer/renderer/stage.py
# Stage floor and grid rendering

import numpy as np
import moderngl
import glm


class StageRenderer:
    """
    Renders the stage floor with grid lines.

    The stage is rendered as a flat plane at Y=0 with:
    - Dark floor surface
    - Grid lines at 1m intervals
    - Center cross marking origin (0,0)
    - Coordinate axes (X=red, Z=blue)
    """

    # Shader sources
    FLOOR_VERTEX_SHADER = """
    #version 330

    in vec3 in_position;

    uniform mat4 mvp;

    void main() {
        gl_Position = mvp * vec4(in_position, 1.0);
    }
    """

    FLOOR_FRAGMENT_SHADER = """
    #version 330

    out vec4 fragColor;

    uniform vec4 color;

    void main() {
        fragColor = color;
    }
    """

    GRID_VERTEX_SHADER = """
    #version 330

    in vec3 in_position;
    in vec3 in_color;

    out vec3 v_color;

    uniform mat4 mvp;

    void main() {
        gl_Position = mvp * vec4(in_position, 1.0);
        v_color = in_color;
    }
    """

    GRID_FRAGMENT_SHADER = """
    #version 330

    in vec3 v_color;

    out vec4 fragColor;

    void main() {
        fragColor = vec4(v_color, 1.0);
    }
    """

    def __init__(self, ctx: moderngl.Context, width: float = 10.0, depth: float = 6.0):
        """
        Initialize stage renderer.

        Args:
            ctx: ModernGL context
            width: Stage width in meters
            depth: Stage depth in meters
        """
        self.ctx = ctx
        self.width = width
        self.depth = depth

        # Grid spacing in meters
        self.grid_spacing = 1.0

        # Colors - made brighter for visibility
        self.floor_color = (0.15, 0.15, 0.2, 1.0)  # Dark blue-gray
        self.grid_color = (0.5, 0.5, 0.55)  # Brighter gray for grid lines
        self.axis_x_color = (1.0, 0.3, 0.3)  # Bright red for X axis
        self.axis_z_color = (0.3, 0.3, 1.0)  # Bright blue for Z axis
        self.center_color = (1.0, 1.0, 1.0)  # White for center cross

        # Create shaders
        try:
            self.floor_program = ctx.program(
                vertex_shader=self.FLOOR_VERTEX_SHADER,
                fragment_shader=self.FLOOR_FRAGMENT_SHADER
            )
            print(f"Floor shader compiled OK")
        except Exception as e:
            print(f"Floor shader error: {e}")
            raise

        try:
            self.grid_program = ctx.program(
                vertex_shader=self.GRID_VERTEX_SHADER,
                fragment_shader=self.GRID_FRAGMENT_SHADER
            )
            print(f"Grid shader compiled OK")
        except Exception as e:
            print(f"Grid shader error: {e}")
            raise

        # Create geometry
        self._create_floor()
        self._create_grid()
        print(f"Stage geometry created: floor={self.width}x{self.depth}m, grid vertices={self.grid_vertex_count}")

    def _create_floor(self):
        """Create floor quad geometry."""
        half_w = self.width / 2
        half_d = self.depth / 2

        # Floor vertices (two triangles forming a quad)
        vertices = np.array([
            # Triangle 1
            -half_w, 0.0, -half_d,
            half_w, 0.0, -half_d,
            half_w, 0.0, half_d,
            # Triangle 2
            -half_w, 0.0, -half_d,
            half_w, 0.0, half_d,
            -half_w, 0.0, half_d,
        ], dtype='f4')

        self.floor_vbo = self.ctx.buffer(vertices.tobytes())
        self.floor_vao = self.ctx.vertex_array(
            self.floor_program,
            [(self.floor_vbo, '3f', 'in_position')]
        )

    def _create_grid(self):
        """Create grid lines geometry."""
        half_w = self.width / 2
        half_d = self.depth / 2

        lines = []

        # Grid offset (slightly above floor to avoid z-fighting)
        y_offset = 0.001
        axis_offset = 0.002  # Axes slightly above grid lines

        # FIRST: Always draw the center axes explicitly (regardless of grid spacing)
        # Y axis (depth direction, at x=0) - BLUE
        lines.extend([0.0, axis_offset, -half_d, *self.axis_z_color])
        lines.extend([0.0, axis_offset, half_d, *self.axis_z_color])

        # X axis (width direction, at z=0) - RED
        lines.extend([-half_w, axis_offset, 0.0, *self.axis_x_color])
        lines.extend([half_w, axis_offset, 0.0, *self.axis_x_color])

        # THEN: Draw grid lines at regular intervals from center outward
        # This ensures grid lines are always at integer meter positions from center

        # Vertical lines (along Z/depth axis) - positive X direction
        x = self.grid_spacing
        while x <= half_w + 0.001:
            lines.extend([x, y_offset, -half_d, *self.grid_color])
            lines.extend([x, y_offset, half_d, *self.grid_color])
            x += self.grid_spacing

        # Vertical lines - negative X direction
        x = -self.grid_spacing
        while x >= -half_w - 0.001:
            lines.extend([x, y_offset, -half_d, *self.grid_color])
            lines.extend([x, y_offset, half_d, *self.grid_color])
            x -= self.grid_spacing

        # Horizontal lines (along X/width axis) - positive Z direction
        z = self.grid_spacing
        while z <= half_d + 0.001:
            lines.extend([-half_w, y_offset, z, *self.grid_color])
            lines.extend([half_w, y_offset, z, *self.grid_color])
            z += self.grid_spacing

        # Horizontal lines - negative Z direction
        z = -self.grid_spacing
        while z >= -half_d - 0.001:
            lines.extend([-half_w, y_offset, z, *self.grid_color])
            lines.extend([half_w, y_offset, z, *self.grid_color])
            z -= self.grid_spacing

        # Center cross (more visible, white)
        cross_size = 0.2
        lines.extend([-cross_size, axis_offset + 0.001, 0.0, *self.center_color])
        lines.extend([cross_size, axis_offset + 0.001, 0.0, *self.center_color])
        lines.extend([0.0, axis_offset + 0.001, -cross_size, *self.center_color])
        lines.extend([0.0, axis_offset + 0.001, cross_size, *self.center_color])

        vertices = np.array(lines, dtype='f4')

        self.grid_vbo = self.ctx.buffer(vertices.tobytes())
        self.grid_vao = self.ctx.vertex_array(
            self.grid_program,
            [(self.grid_vbo, '3f 3f', 'in_position', 'in_color')]
        )
        self.grid_vertex_count = len(lines) // 6  # 6 floats per vertex (pos + color)

    def set_size(self, width: float, depth: float):
        """
        Update stage dimensions.

        Args:
            width: New width in meters
            depth: New depth in meters
        """
        if width != self.width or depth != self.depth:
            self.width = width
            self.depth = depth

            # Release old buffers before creating new ones
            if hasattr(self, 'floor_vbo') and self.floor_vbo:
                self.floor_vbo.release()
            if hasattr(self, 'floor_vao') and self.floor_vao:
                self.floor_vao.release()
            if hasattr(self, 'grid_vbo') and self.grid_vbo:
                self.grid_vbo.release()
            if hasattr(self, 'grid_vao') and self.grid_vao:
                self.grid_vao.release()

            # Recreate geometry
            self._create_floor()
            self._create_grid()
            print(f"Stage resized to {width}x{depth}m")

    def set_grid_size(self, grid_size: float):
        """
        Update grid spacing.

        Args:
            grid_size: New grid spacing in meters
        """
        if grid_size != self.grid_spacing and grid_size > 0:
            self.grid_spacing = grid_size

            # Release old grid buffers
            if hasattr(self, 'grid_vbo') and self.grid_vbo:
                self.grid_vbo.release()
            if hasattr(self, 'grid_vao') and self.grid_vao:
                self.grid_vao.release()

            # Recreate grid geometry
            self._create_grid()
            print(f"Grid spacing changed to {grid_size}m")

    def render(self, mvp: glm.mat4):
        """
        Render the stage.

        Args:
            mvp: Model-View-Projection matrix
        """
        # Convert glm matrix to bytes for ModernGL
        # glm.mat4.to_list() returns nested list [[col0], [col1], ...], need to flatten
        mvp_flat = []
        for col in mvp.to_list():
            mvp_flat.extend(col)
        mvp_bytes = np.array(mvp_flat, dtype='f4').tobytes()


        # Render floor
        self.floor_program['mvp'].write(mvp_bytes)
        self.floor_program['color'].value = self.floor_color
        self.floor_vao.render(moderngl.TRIANGLES)

        # Render grid lines
        self.grid_program['mvp'].write(mvp_bytes)
        self.grid_vao.render(moderngl.LINES)

    def release(self):
        """Release GPU resources."""
        self.floor_vbo.release()
        self.floor_vao.release()
        self.grid_vbo.release()
        self.grid_vao.release()
        self.floor_program.release()
        self.grid_program.release()
