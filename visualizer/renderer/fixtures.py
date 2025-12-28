# visualizer/renderer/fixtures.py
# Fixture rendering for the 3D visualizer

import math
import numpy as np
import moderngl
import glm
from typing import Dict, List, Any, Optional, Tuple
from abc import ABC, abstractmethod


# Warm white color temperature (~2700K)
WARM_WHITE_COLOR = (1.0, 0.85, 0.6)  # RGB approximation of warm white


class GeometryBuilder:
    """Utility class for building procedural geometry."""

    @staticmethod
    def create_box(width: float, height: float, depth: float,
                   center: Tuple[float, float, float] = (0, 0, 0)) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create a box mesh.

        Args:
            width: Box width (X axis)
            height: Box height (Y axis)
            depth: Box depth (Z axis)
            center: Center position

        Returns:
            Tuple of (vertices, normals) as numpy arrays
        """
        hw, hh, hd = width / 2, height / 2, depth / 2
        cx, cy, cz = center

        # 6 faces, 2 triangles each, 3 vertices per triangle = 36 vertices
        vertices = []
        normals = []

        # Front face (+Z)
        vertices.extend([
            cx - hw, cy - hh, cz + hd,
            cx + hw, cy - hh, cz + hd,
            cx + hw, cy + hh, cz + hd,
            cx - hw, cy - hh, cz + hd,
            cx + hw, cy + hh, cz + hd,
            cx - hw, cy + hh, cz + hd,
        ])
        normals.extend([0, 0, 1] * 6)

        # Back face (-Z)
        vertices.extend([
            cx + hw, cy - hh, cz - hd,
            cx - hw, cy - hh, cz - hd,
            cx - hw, cy + hh, cz - hd,
            cx + hw, cy - hh, cz - hd,
            cx - hw, cy + hh, cz - hd,
            cx + hw, cy + hh, cz - hd,
        ])
        normals.extend([0, 0, -1] * 6)

        # Right face (+X)
        vertices.extend([
            cx + hw, cy - hh, cz + hd,
            cx + hw, cy - hh, cz - hd,
            cx + hw, cy + hh, cz - hd,
            cx + hw, cy - hh, cz + hd,
            cx + hw, cy + hh, cz - hd,
            cx + hw, cy + hh, cz + hd,
        ])
        normals.extend([1, 0, 0] * 6)

        # Left face (-X)
        vertices.extend([
            cx - hw, cy - hh, cz - hd,
            cx - hw, cy - hh, cz + hd,
            cx - hw, cy + hh, cz + hd,
            cx - hw, cy - hh, cz - hd,
            cx - hw, cy + hh, cz + hd,
            cx - hw, cy + hh, cz - hd,
        ])
        normals.extend([-1, 0, 0] * 6)

        # Top face (+Y)
        vertices.extend([
            cx - hw, cy + hh, cz + hd,
            cx + hw, cy + hh, cz + hd,
            cx + hw, cy + hh, cz - hd,
            cx - hw, cy + hh, cz + hd,
            cx + hw, cy + hh, cz - hd,
            cx - hw, cy + hh, cz - hd,
        ])
        normals.extend([0, 1, 0] * 6)

        # Bottom face (-Y)
        vertices.extend([
            cx - hw, cy - hh, cz - hd,
            cx + hw, cy - hh, cz - hd,
            cx + hw, cy - hh, cz + hd,
            cx - hw, cy - hh, cz - hd,
            cx + hw, cy - hh, cz + hd,
            cx - hw, cy - hh, cz + hd,
        ])
        normals.extend([0, -1, 0] * 6)

        return np.array(vertices, dtype='f4'), np.array(normals, dtype='f4')

    @staticmethod
    def create_cylinder(radius: float, height: float, segments: int = 16,
                        center: Tuple[float, float, float] = (0, 0, 0)) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create a cylinder mesh oriented along Y axis.

        Args:
            radius: Cylinder radius
            height: Cylinder height
            segments: Number of segments around circumference
            center: Center position

        Returns:
            Tuple of (vertices, normals) as numpy arrays
        """
        cx, cy, cz = center
        hh = height / 2

        vertices = []
        normals = []

        # Side faces
        for i in range(segments):
            angle1 = 2 * math.pi * i / segments
            angle2 = 2 * math.pi * (i + 1) / segments

            x1, z1 = math.cos(angle1) * radius, math.sin(angle1) * radius
            x2, z2 = math.cos(angle2) * radius, math.sin(angle2) * radius

            # Two triangles for this segment
            # Triangle 1
            vertices.extend([
                cx + x1, cy - hh, cz + z1,
                cx + x2, cy - hh, cz + z2,
                cx + x2, cy + hh, cz + z2,
            ])
            normals.extend([
                math.cos(angle1), 0, math.sin(angle1),
                math.cos(angle2), 0, math.sin(angle2),
                math.cos(angle2), 0, math.sin(angle2),
            ])

            # Triangle 2
            vertices.extend([
                cx + x1, cy - hh, cz + z1,
                cx + x2, cy + hh, cz + z2,
                cx + x1, cy + hh, cz + z1,
            ])
            normals.extend([
                math.cos(angle1), 0, math.sin(angle1),
                math.cos(angle2), 0, math.sin(angle2),
                math.cos(angle1), 0, math.sin(angle1),
            ])

        # Top cap
        for i in range(segments):
            angle1 = 2 * math.pi * i / segments
            angle2 = 2 * math.pi * (i + 1) / segments

            x1, z1 = math.cos(angle1) * radius, math.sin(angle1) * radius
            x2, z2 = math.cos(angle2) * radius, math.sin(angle2) * radius

            vertices.extend([
                cx, cy + hh, cz,
                cx + x1, cy + hh, cz + z1,
                cx + x2, cy + hh, cz + z2,
            ])
            normals.extend([0, 1, 0] * 3)

        # Bottom cap
        for i in range(segments):
            angle1 = 2 * math.pi * i / segments
            angle2 = 2 * math.pi * (i + 1) / segments

            x1, z1 = math.cos(angle1) * radius, math.sin(angle1) * radius
            x2, z2 = math.cos(angle2) * radius, math.sin(angle2) * radius

            vertices.extend([
                cx, cy - hh, cz,
                cx + x2, cy - hh, cz + z2,
                cx + x1, cy - hh, cz + z1,
            ])
            normals.extend([0, -1, 0] * 3)

        return np.array(vertices, dtype='f4'), np.array(normals, dtype='f4')

    @staticmethod
    def create_beam_cone(base_radius: float, length: float, segments: int = 16) -> Tuple[np.ndarray, np.ndarray]:
        """
        Create a beam cone mesh for volumetric lighting.

        The cone starts at origin and extends along +Z axis.
        Alpha values are 1.0 at tip, fading to 0.0 at base edges.

        Args:
            base_radius: Radius at the base of the cone
            length: Length of the cone
            segments: Number of segments around circumference

        Returns:
            Tuple of (vertices, alphas) as numpy arrays
        """
        vertices = []
        alphas = []

        # Cone from tip (0,0,0) to base at z=length
        for i in range(segments):
            angle1 = 2 * math.pi * i / segments
            angle2 = 2 * math.pi * (i + 1) / segments

            x1, y1 = math.cos(angle1) * base_radius, math.sin(angle1) * base_radius
            x2, y2 = math.cos(angle2) * base_radius, math.sin(angle2) * base_radius

            # Triangle from tip to two base vertices
            # Tip vertex (bright)
            vertices.extend([0, 0, 0])
            alphas.append(1.0)

            # Base vertex 1 (dim)
            vertices.extend([x1, y1, length])
            alphas.append(0.0)

            # Base vertex 2 (dim)
            vertices.extend([x2, y2, length])
            alphas.append(0.0)

        return np.array(vertices, dtype='f4'), np.array(alphas, dtype='f4')


# Shared shader for fixture body rendering
FIXTURE_VERTEX_SHADER = """
#version 330

in vec3 in_position;
in vec3 in_normal;

out vec3 v_normal;
out vec3 v_position;

uniform mat4 mvp;
uniform mat4 model;

void main() {
    gl_Position = mvp * vec4(in_position, 1.0);
    v_normal = mat3(model) * in_normal;
    v_position = (model * vec4(in_position, 1.0)).xyz;
}
"""

FIXTURE_FRAGMENT_SHADER = """
#version 330

in vec3 v_normal;
in vec3 v_position;

out vec4 fragColor;

uniform vec3 base_color;
uniform vec3 emissive_color;
uniform float emissive_strength;

void main() {
    // Simple directional lighting
    vec3 light_dir = normalize(vec3(0.5, 1.0, 0.3));
    float diff = max(dot(normalize(v_normal), light_dir), 0.0);

    // Ambient + diffuse lighting on base color
    vec3 ambient = base_color * 0.3;
    vec3 diffuse = base_color * diff * 0.7;

    // Add emissive glow
    vec3 emissive = emissive_color * emissive_strength;

    vec3 final_color = ambient + diffuse + emissive;
    fragColor = vec4(final_color, 1.0);
}
"""

# Beam shader for volumetric light cone
BEAM_VERTEX_SHADER = """
#version 330

in vec3 in_position;
in float in_alpha;

out float v_alpha;

uniform mat4 mvp;

void main() {
    gl_Position = mvp * vec4(in_position, 1.0);
    v_alpha = in_alpha;
}
"""

BEAM_FRAGMENT_SHADER = """
#version 330

in float v_alpha;

out vec4 fragColor;

uniform vec3 beam_color;
uniform float beam_intensity;

void main() {
    // Fade out toward edges and along length
    float alpha = v_alpha * beam_intensity * 0.3;
    fragColor = vec4(beam_color, alpha);
}
"""


class FixtureRenderer(ABC):
    """Base class for fixture renderers."""

    def __init__(self, ctx: moderngl.Context, fixture_data: Dict[str, Any]):
        """
        Initialize fixture renderer.

        Args:
            ctx: ModernGL context
            fixture_data: Fixture data from TCP message
        """
        self.ctx = ctx
        self.fixture_data = fixture_data

        # Extract common properties
        self.name = fixture_data.get('name', 'Unknown')
        self.position = fixture_data.get('position', {'x': 0, 'y': 0, 'z': 0})
        self.rotation = fixture_data.get('rotation', 0.0)
        self.universe = fixture_data.get('universe', 1)
        self.address = fixture_data.get('address', 1)
        self.channel_mapping = fixture_data.get('channel_mapping', {})

        # Physical dimensions (in meters)
        physical = fixture_data.get('physical', {'width': 0.3, 'height': 0.3, 'depth': 0.2})
        self.width = physical.get('width', 0.3)
        self.height = physical.get('height', 0.3)
        self.depth = physical.get('depth', 0.2)

        # Layout for segmented fixtures
        layout = fixture_data.get('layout', {'width': 1, 'height': 1})
        self.segment_cols = layout.get('width', 1)
        self.segment_rows = layout.get('height', 1)

        # Beam properties
        self.beam_angle = fixture_data.get('beam_angle', 25.0)

        # Current DMX state
        self.dmx_values: Dict[str, int] = {}
        self.segment_values: List[int] = []  # Per-segment DMX values

        # GPU resources (to be created by subclasses)
        self.program: Optional[moderngl.Program] = None
        self.vao: Optional[moderngl.VertexArray] = None
        self.vbo: Optional[moderngl.Buffer] = None
        self.nbo: Optional[moderngl.Buffer] = None

    def get_model_matrix(self) -> glm.mat4:
        """Get the model transformation matrix for this fixture."""
        # Start with identity
        model = glm.mat4(1.0)

        # Translate to position
        # Note: In the visualizer, Y is up, so we map:
        # Stage X -> 3D X
        # Stage Y -> 3D Z (depth)
        # Stage Z (height) -> 3D Y (up)
        pos = self.position
        model = glm.translate(model, glm.vec3(pos['x'], pos['z'], pos['y']))

        # Rotate around Y axis (vertical)
        model = glm.rotate(model, glm.radians(self.rotation), glm.vec3(0, 1, 0))

        return model

    def update_dmx(self, dmx_data: bytes):
        """
        Update fixture state from DMX data.

        Args:
            dmx_data: 512 bytes of DMX data for the universe
        """
        # Convert channel mapping (string keys from JSON to int)
        # ch_num is 0-indexed (channel offset within fixture mode)
        # self.address is 1-indexed DMX address
        for ch_str, func in self.channel_mapping.items():
            try:
                ch_num = int(ch_str)
                # Calculate array index: (address - 1) converts to 0-indexed, + ch_num for offset
                index = (self.address - 1) + ch_num
                if 0 <= index < 512:
                    self.dmx_values[func] = dmx_data[index]
            except (ValueError, IndexError):
                pass

        # Also store raw DMX values for segment-based fixtures
        # (sunstrips, LED bars with per-segment control)
        self._update_segment_dmx(dmx_data)

    def _update_segment_dmx(self, dmx_data: bytes):
        """
        Update per-segment DMX values. Override in segment-based fixtures.

        Args:
            dmx_data: 512 bytes of DMX data
        """
        # Default: store raw channel values for segment count
        # Subclasses can override for specific behavior
        self.segment_values = []
        base_index = self.address - 1  # Convert to 0-indexed

        for i in range(self.segment_cols * self.segment_rows):
            if base_index + i < 512:
                self.segment_values.append(dmx_data[base_index + i])
            else:
                self.segment_values.append(0)

    def get_color(self) -> Tuple[float, float, float]:
        """Get current RGB color from DMX values (0-1 range)."""
        r = self.dmx_values.get('red', 0) / 255.0
        g = self.dmx_values.get('green', 0) / 255.0
        b = self.dmx_values.get('blue', 0) / 255.0
        return (r, g, b)

    def get_dimmer(self) -> float:
        """Get current dimmer value (0-1 range)."""
        # Default to 0 (off) when no DMX received, not 255
        return self.dmx_values.get('dimmer', 0) / 255.0

    @abstractmethod
    def render(self, mvp: glm.mat4):
        """Render the fixture."""
        pass

    def release(self):
        """Release GPU resources."""
        if self.vao:
            self.vao.release()
        if self.vbo:
            self.vbo.release()
        if self.nbo:
            self.nbo.release()
        if self.program:
            self.program.release()


class LEDBarRenderer(FixtureRenderer):
    """Renderer for LED bar fixtures with RGBW segments."""

    # Body color (dark metal)
    BODY_COLOR = (0.15, 0.15, 0.18)

    def __init__(self, ctx: moderngl.Context, fixture_data: Dict[str, Any]):
        super().__init__(ctx, fixture_data)
        self._create_geometry()

    def _create_geometry(self):
        """Create bar body and segment geometry."""
        # Create shader program
        self.program = self.ctx.program(
            vertex_shader=FIXTURE_VERTEX_SHADER,
            fragment_shader=FIXTURE_FRAGMENT_SHADER
        )

        # Create bar body (housing)
        body_verts, body_norms = GeometryBuilder.create_box(
            self.width, self.height, self.depth
        )

        self.vbo = self.ctx.buffer(body_verts.tobytes())
        self.nbo = self.ctx.buffer(body_norms.tobytes())

        self.vao = self.ctx.vertex_array(
            self.program,
            [
                (self.vbo, '3f', 'in_position'),
                (self.nbo, '3f', 'in_normal'),
            ]
        )
        self.body_vertex_count = len(body_verts) // 3

        # Create segment geometry (lens/emitter surfaces)
        segment_width = (self.width * 0.9) / self.segment_cols
        segment_height = self.height * 0.6
        segment_depth = 0.01  # Thin emitter surface

        segment_verts = []
        segment_norms = []

        start_x = -self.width * 0.45 + segment_width / 2

        for i in range(self.segment_cols):
            x_offset = start_x + i * segment_width
            verts, norms = GeometryBuilder.create_box(
                segment_width * 0.85,
                segment_height,
                segment_depth,
                center=(x_offset, 0, self.depth / 2 + segment_depth / 2)
            )
            segment_verts.extend(verts)
            segment_norms.extend(norms)

        self.segment_vbo = self.ctx.buffer(np.array(segment_verts, dtype='f4').tobytes())
        self.segment_nbo = self.ctx.buffer(np.array(segment_norms, dtype='f4').tobytes())

        self.segment_vao = self.ctx.vertex_array(
            self.program,
            [
                (self.segment_vbo, '3f', 'in_position'),
                (self.segment_nbo, '3f', 'in_normal'),
            ]
        )
        self.segment_vertex_count = len(segment_verts) // 3
        self.vertices_per_segment = self.segment_vertex_count // self.segment_cols

    def render(self, mvp: glm.mat4):
        """Render the LED bar."""
        model = self.get_model_matrix()
        final_mvp = mvp * model

        # Convert matrices to bytes
        mvp_bytes = np.array([x for col in final_mvp.to_list() for x in col], dtype='f4').tobytes()
        model_bytes = np.array([x for col in model.to_list() for x in col], dtype='f4').tobytes()

        self.program['mvp'].write(mvp_bytes)
        self.program['model'].write(model_bytes)

        # Render body
        self.program['base_color'].value = self.BODY_COLOR
        self.program['emissive_color'].value = (0.0, 0.0, 0.0)
        self.program['emissive_strength'].value = 0.0
        self.vao.render(moderngl.TRIANGLES)

        # Render segments with their colors
        color = self.get_color()
        dimmer = self.get_dimmer()

        # Add white channel contribution
        white = self.dmx_values.get('white', 0) / 255.0
        color = (
            min(1.0, color[0] + white),
            min(1.0, color[1] + white),
            min(1.0, color[2] + white)
        )

        # Apply dimmer
        emissive = (color[0] * dimmer, color[1] * dimmer, color[2] * dimmer)

        self.program['base_color'].value = (0.1, 0.1, 0.1)
        self.program['emissive_color'].value = emissive
        self.program['emissive_strength'].value = 1.0

        self.segment_vao.render(moderngl.TRIANGLES)

    def release(self):
        """Release GPU resources."""
        super().release()
        if hasattr(self, 'segment_vao') and self.segment_vao:
            self.segment_vao.release()
        if hasattr(self, 'segment_vbo') and self.segment_vbo:
            self.segment_vbo.release()
        if hasattr(self, 'segment_nbo') and self.segment_nbo:
            self.segment_nbo.release()


class SunstripRenderer(FixtureRenderer):
    """Renderer for sunstrip fixtures with warm white segments."""

    BODY_COLOR = (0.12, 0.12, 0.15)

    def __init__(self, ctx: moderngl.Context, fixture_data: Dict[str, Any]):
        super().__init__(ctx, fixture_data)
        self._create_geometry()

    def _create_geometry(self):
        """Create sunstrip body and lamp geometry."""
        self.program = self.ctx.program(
            vertex_shader=FIXTURE_VERTEX_SHADER,
            fragment_shader=FIXTURE_FRAGMENT_SHADER
        )

        # Create bar body
        body_verts, body_norms = GeometryBuilder.create_box(
            self.width, self.height, self.depth
        )

        self.vbo = self.ctx.buffer(body_verts.tobytes())
        self.nbo = self.ctx.buffer(body_norms.tobytes())

        self.vao = self.ctx.vertex_array(
            self.program,
            [
                (self.vbo, '3f', 'in_position'),
                (self.nbo, '3f', 'in_normal'),
            ]
        )

        # Create individual lamp bulbs (cylinders)
        lamp_radius = min(self.width / self.segment_cols * 0.35, 0.03)
        lamp_height = 0.02

        lamp_verts = []
        lamp_norms = []

        spacing = self.width * 0.9 / self.segment_cols
        start_x = -self.width * 0.45 + spacing / 2

        for i in range(self.segment_cols):
            x_offset = start_x + i * spacing
            verts, norms = GeometryBuilder.create_cylinder(
                lamp_radius, lamp_height, segments=12,
                center=(x_offset, self.height / 2 + lamp_height / 2, 0)
            )
            lamp_verts.extend(verts)
            lamp_norms.extend(norms)

        self.lamp_vbo = self.ctx.buffer(np.array(lamp_verts, dtype='f4').tobytes())
        self.lamp_nbo = self.ctx.buffer(np.array(lamp_norms, dtype='f4').tobytes())

        self.lamp_vao = self.ctx.vertex_array(
            self.program,
            [
                (self.lamp_vbo, '3f', 'in_position'),
                (self.lamp_nbo, '3f', 'in_normal'),
            ]
        )
        self.lamp_vertex_count = len(lamp_verts) // 3
        self.vertices_per_lamp = self.lamp_vertex_count // self.segment_cols

    def render(self, mvp: glm.mat4):
        """Render the sunstrip with per-segment dimming."""
        model = self.get_model_matrix()
        final_mvp = mvp * model

        mvp_bytes = np.array([x for col in final_mvp.to_list() for x in col], dtype='f4').tobytes()
        model_bytes = np.array([x for col in model.to_list() for x in col], dtype='f4').tobytes()

        self.program['mvp'].write(mvp_bytes)
        self.program['model'].write(model_bytes)

        # Render body
        self.program['base_color'].value = self.BODY_COLOR
        self.program['emissive_color'].value = (0.0, 0.0, 0.0)
        self.program['emissive_strength'].value = 0.0
        self.vao.render(moderngl.TRIANGLES)

        # Render each lamp segment with its own dimmer value
        self.program['base_color'].value = (0.9, 0.85, 0.7)  # Bulb glass color

        # Get per-segment DMX values (or fall back to single dimmer)
        segment_values = getattr(self, 'segment_values', [])

        for i in range(self.segment_cols):
            # Get dimmer for this segment
            if i < len(segment_values):
                dimmer = segment_values[i] / 255.0
            else:
                dimmer = self.get_dimmer()

            emissive = (
                WARM_WHITE_COLOR[0] * dimmer,
                WARM_WHITE_COLOR[1] * dimmer,
                WARM_WHITE_COLOR[2] * dimmer
            )

            self.program['emissive_color'].value = emissive
            self.program['emissive_strength'].value = 1.5 if dimmer > 0.1 else 0.0

            # Render just this lamp's vertices
            first_vertex = i * self.vertices_per_lamp
            self.lamp_vao.render(
                moderngl.TRIANGLES,
                vertices=self.vertices_per_lamp,
                first=first_vertex
            )

    def release(self):
        """Release GPU resources."""
        super().release()
        if hasattr(self, 'lamp_vao') and self.lamp_vao:
            self.lamp_vao.release()
        if hasattr(self, 'lamp_vbo') and self.lamp_vbo:
            self.lamp_vbo.release()
        if hasattr(self, 'lamp_nbo') and self.lamp_nbo:
            self.lamp_nbo.release()


class MovingHeadRenderer(FixtureRenderer):
    """Renderer for moving head fixtures with base, yoke, and head."""

    BODY_COLOR = (0.1, 0.1, 0.12)
    YOKE_COLOR = (0.15, 0.15, 0.18)

    def __init__(self, ctx: moderngl.Context, fixture_data: Dict[str, Any]):
        super().__init__(ctx, fixture_data)

        # Movement range
        self.pan_max = fixture_data.get('pan_max', 540.0)
        self.tilt_max = fixture_data.get('tilt_max', 270.0)

        # Color wheel data - list of {min, max, color} dicts
        self.color_wheel = fixture_data.get('color_wheel', [])

        # Current pan/tilt angles (degrees)
        self.current_pan = 0.0
        self.current_tilt = 0.0

        self._create_geometry()

    def get_color_from_wheel(self, dmx_value: int) -> Tuple[float, float, float]:
        """
        Get RGB color from color wheel based on DMX value.

        Args:
            dmx_value: DMX value (0-255)

        Returns:
            RGB tuple (0.0-1.0)
        """
        if not self.color_wheel:
            return (1.0, 1.0, 1.0)  # Default white

        for entry in self.color_wheel:
            if entry['min'] <= dmx_value <= entry['max']:
                color_hex = entry['color']
                # Parse hex color
                if color_hex.startswith('#'):
                    color_hex = color_hex[1:]
                try:
                    r = int(color_hex[0:2], 16) / 255.0
                    g = int(color_hex[2:4], 16) / 255.0
                    b = int(color_hex[4:6], 16) / 255.0
                    return (r, g, b)
                except (ValueError, IndexError):
                    pass

        return (1.0, 1.0, 1.0)  # Default white if no match

    def get_color(self) -> Tuple[float, float, float]:
        """Get current color, using color wheel if available."""
        # First check if we have RGB channels
        color = super().get_color()

        # If no RGB color and we have a color wheel, use it
        if color == (0.0, 0.0, 0.0) and self.color_wheel:
            color_wheel_value = self.dmx_values.get('color_wheel', 0)
            wheel_color = self.get_color_from_wheel(color_wheel_value)
            # Debug: log color wheel usage occasionally
            if not hasattr(self, '_color_log_count'):
                self._color_log_count = 0
            if self._color_log_count < 3 and color_wheel_value > 0:
                self._color_log_count += 1
                print(f"MH {self.name}: color_wheel DMX={color_wheel_value} -> RGB={wheel_color}")
            return wheel_color

        # If still no color from wheel (no wheel data), use white as fallback
        if color == (0.0, 0.0, 0.0):
            return (1.0, 1.0, 1.0)

        return color

    def _create_geometry(self):
        """Create base, yoke, and head geometry."""
        self.program = self.ctx.program(
            vertex_shader=FIXTURE_VERTEX_SHADER,
            fragment_shader=FIXTURE_FRAGMENT_SHADER
        )

        # Proportions based on physical dimensions
        base_size = min(self.width, self.depth)
        base_height = self.height * 0.25

        yoke_width = base_size * 0.15
        yoke_height = self.height * 0.5
        yoke_depth = base_size * 0.8

        head_width = base_size * 0.7
        head_height = self.height * 0.45
        head_depth = base_size * 0.5

        # Create base (cylinder)
        base_verts, base_norms = GeometryBuilder.create_cylinder(
            base_size / 2, base_height, segments=24,
            center=(0, base_height / 2, 0)
        )
        self.base_vbo = self.ctx.buffer(base_verts.tobytes())
        self.base_nbo = self.ctx.buffer(base_norms.tobytes())
        self.base_vao = self.ctx.vertex_array(
            self.program,
            [(self.base_vbo, '3f', 'in_position'), (self.base_nbo, '3f', 'in_normal')]
        )
        self.base_vertex_count = len(base_verts) // 3

        # Create yoke arms (two vertical pieces)
        yoke_y = base_height + yoke_height / 2
        left_yoke_verts, left_yoke_norms = GeometryBuilder.create_box(
            yoke_width, yoke_height, yoke_depth,
            center=(-head_width / 2 - yoke_width / 2, yoke_y, 0)
        )
        right_yoke_verts, right_yoke_norms = GeometryBuilder.create_box(
            yoke_width, yoke_height, yoke_depth,
            center=(head_width / 2 + yoke_width / 2, yoke_y, 0)
        )
        yoke_verts = np.concatenate([left_yoke_verts, right_yoke_verts])
        yoke_norms = np.concatenate([left_yoke_norms, right_yoke_norms])

        self.yoke_vbo = self.ctx.buffer(yoke_verts.tobytes())
        self.yoke_nbo = self.ctx.buffer(yoke_norms.tobytes())
        self.yoke_vao = self.ctx.vertex_array(
            self.program,
            [(self.yoke_vbo, '3f', 'in_position'), (self.yoke_nbo, '3f', 'in_normal')]
        )
        self.yoke_vertex_count = len(yoke_verts) // 3

        # Create head (box, will be rotated for tilt)
        # Head is created at origin, transformed during render
        head_verts, head_norms = GeometryBuilder.create_box(
            head_width, head_height, head_depth
        )
        self.head_vbo = self.ctx.buffer(head_verts.tobytes())
        self.head_nbo = self.ctx.buffer(head_norms.tobytes())
        self.head_vao = self.ctx.vertex_array(
            self.program,
            [(self.head_vbo, '3f', 'in_position'), (self.head_nbo, '3f', 'in_normal')]
        )
        self.head_vertex_count = len(head_verts) // 3

        # Create lens (cylinder on front of head)
        lens_radius = min(head_width, head_height) * 0.35
        lens_depth = 0.02

        lens_verts, lens_norms = GeometryBuilder.create_cylinder(
            lens_radius, lens_depth, segments=24,
            center=(0, 0, head_depth / 2 + lens_depth / 2)
        )
        # Rotate lens to face forward (cylinder is Y-oriented, need Z-oriented)
        # We'll handle this in the shader by storing it correctly
        self.lens_vbo = self.ctx.buffer(lens_verts.tobytes())
        self.lens_nbo = self.ctx.buffer(lens_norms.tobytes())
        self.lens_vao = self.ctx.vertex_array(
            self.program,
            [(self.lens_vbo, '3f', 'in_position'), (self.lens_nbo, '3f', 'in_normal')]
        )
        self.lens_vertex_count = len(lens_verts) // 3

        # Store dimensions for head positioning
        self.base_height = base_height
        self.yoke_height = yoke_height
        self.head_height = head_height
        self.head_depth = head_depth
        self.lens_radius = lens_radius

        # Create beam cone for light visualization
        self._create_beam_geometry()

    def _create_beam_geometry(self):
        """Create beam cone geometry for light visualization."""
        # Beam program with transparency support
        self.beam_program = self.ctx.program(
            vertex_shader=BEAM_VERTEX_SHADER,
            fragment_shader=BEAM_FRAGMENT_SHADER
        )

        # Calculate beam radius at 5m distance based on beam angle
        beam_length = 5.0  # 5 meters
        beam_radius = beam_length * math.tan(math.radians(self.beam_angle / 2))

        beam_verts, beam_alphas = GeometryBuilder.create_beam_cone(
            beam_radius, beam_length, segments=24
        )

        self.beam_vbo = self.ctx.buffer(beam_verts.tobytes())
        self.beam_abo = self.ctx.buffer(beam_alphas.tobytes())

        self.beam_vao = self.ctx.vertex_array(
            self.beam_program,
            [
                (self.beam_vbo, '3f', 'in_position'),
                (self.beam_abo, '1f', 'in_alpha'),
            ]
        )
        self.beam_vertex_count = len(beam_verts) // 3

    def update_dmx(self, dmx_data: bytes):
        """Update DMX values and calculate pan/tilt angles."""
        super().update_dmx(dmx_data)

        # Calculate pan angle from DMX
        pan_coarse = self.dmx_values.get('pan', 127)
        pan_fine = self.dmx_values.get('pan_fine', 0)
        pan_combined = (pan_coarse * 256 + pan_fine) / 65535.0

        # Calculate tilt angle from DMX
        tilt_coarse = self.dmx_values.get('tilt', 127)
        tilt_fine = self.dmx_values.get('tilt_fine', 0)
        tilt_combined = (tilt_coarse * 256 + tilt_fine) / 65535.0

        # Map to actual angle range
        # Pan: centered at 0, ranges from -pan_max/2 to +pan_max/2
        self.current_pan = (pan_combined - 0.5) * self.pan_max

        # Tilt: 0 = pointing up, goes down to tilt_max
        self.current_tilt = tilt_combined * self.tilt_max - self.tilt_max / 2

    def get_beam_direction(self) -> glm.vec3:
        """Get the beam direction vector based on current pan/tilt."""
        # Start with forward direction (0, 0, 1)
        direction = glm.vec3(0, 0, 1)

        # Apply tilt (rotation around X axis)
        tilt_rad = glm.radians(self.current_tilt)
        tilt_mat = glm.rotate(glm.mat4(1.0), tilt_rad, glm.vec3(1, 0, 0))

        # Apply pan (rotation around Y axis)
        pan_rad = glm.radians(self.current_pan)
        pan_mat = glm.rotate(glm.mat4(1.0), pan_rad, glm.vec3(0, 1, 0))

        # Apply fixture rotation
        rot_mat = glm.rotate(glm.mat4(1.0), glm.radians(self.rotation), glm.vec3(0, 1, 0))

        # Combine rotations
        final_mat = rot_mat * pan_mat * tilt_mat
        direction = glm.vec3(final_mat * glm.vec4(direction, 0.0))

        return glm.normalize(direction)

    def render(self, mvp: glm.mat4):
        """Render the moving head with pan/tilt."""
        # Ensure clean OpenGL state at start of render
        # This prevents blend state from leaking from previous fixture's beam rendering
        self.ctx.disable(moderngl.BLEND)
        self.ctx.depth_mask = True

        base_model = self.get_model_matrix()

        # Render base (doesn't rotate with pan)
        base_mvp = mvp * base_model
        mvp_bytes = np.array([x for col in base_mvp.to_list() for x in col], dtype='f4').tobytes()
        model_bytes = np.array([x for col in base_model.to_list() for x in col], dtype='f4').tobytes()

        self.program['mvp'].write(mvp_bytes)
        self.program['model'].write(model_bytes)
        self.program['base_color'].value = self.BODY_COLOR
        self.program['emissive_color'].value = (0.0, 0.0, 0.0)
        self.program['emissive_strength'].value = 0.0

        self.base_vao.render(moderngl.TRIANGLES)

        # Yoke rotates with pan
        pan_rotation = glm.rotate(glm.mat4(1.0), glm.radians(self.current_pan), glm.vec3(0, 1, 0))
        yoke_model = base_model * pan_rotation

        yoke_mvp = mvp * yoke_model
        mvp_bytes = np.array([x for col in yoke_mvp.to_list() for x in col], dtype='f4').tobytes()
        model_bytes = np.array([x for col in yoke_model.to_list() for x in col], dtype='f4').tobytes()

        self.program['mvp'].write(mvp_bytes)
        self.program['model'].write(model_bytes)
        self.program['base_color'].value = self.YOKE_COLOR

        self.yoke_vao.render(moderngl.TRIANGLES)

        # Head rotates with pan and tilt
        # Position head in yoke, then apply tilt
        head_y = self.base_height + self.yoke_height / 2
        head_translate = glm.translate(glm.mat4(1.0), glm.vec3(0, head_y, 0))

        tilt_rotation = glm.rotate(glm.mat4(1.0), glm.radians(self.current_tilt), glm.vec3(1, 0, 0))

        head_model = base_model * pan_rotation * head_translate * tilt_rotation

        head_mvp = mvp * head_model
        mvp_bytes = np.array([x for col in head_mvp.to_list() for x in col], dtype='f4').tobytes()
        model_bytes = np.array([x for col in head_model.to_list() for x in col], dtype='f4').tobytes()

        self.program['mvp'].write(mvp_bytes)
        self.program['model'].write(model_bytes)
        self.program['base_color'].value = self.BODY_COLOR

        self.head_vao.render(moderngl.TRIANGLES)

        # Render lens with emissive color
        color = self.get_color()  # Handles color wheel and white fallback
        dimmer = self.get_dimmer()

        emissive = (color[0] * dimmer, color[1] * dimmer, color[2] * dimmer)

        self.program['base_color'].value = (0.2, 0.2, 0.2)
        self.program['emissive_color'].value = emissive
        self.program['emissive_strength'].value = 1.0

        self.lens_vao.render(moderngl.TRIANGLES)

        # Render beam if dimmer is on
        if dimmer > 0.01:
            self._render_beam(mvp, head_model, color, dimmer)

    def _render_beam(self, mvp: glm.mat4, head_model: glm.mat4,
                     color: Tuple[float, float, float], dimmer: float):
        """Render the light beam cone."""
        try:
            # Check if beam resources exist
            if not hasattr(self, 'beam_vao') or self.beam_vao is None:
                return

            # Beam starts at lens position and extends in tilt direction
            # Offset beam to start at lens front
            beam_offset = glm.translate(glm.mat4(1.0), glm.vec3(0, 0, self.head_depth / 2 + 0.02))

            # Rotate beam to point along Z axis (our beam cone extends along +Z)
            # Since the head already has tilt applied, beam just needs to extend forward
            beam_model = head_model * beam_offset

            beam_mvp = mvp * beam_model
            mvp_bytes = np.array([x for col in beam_mvp.to_list() for x in col], dtype='f4').tobytes()

            # Enable blending for transparency (additive blending)
            self.ctx.enable(moderngl.BLEND)
            # Default blend equation is ADD, just set the blend function
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE)

            # Disable depth write so beams don't occlude each other
            self.ctx.depth_mask = False

            self.beam_program['mvp'].write(mvp_bytes)
            self.beam_program['beam_color'].value = color
            self.beam_program['beam_intensity'].value = dimmer

            self.beam_vao.render(moderngl.TRIANGLES)

            # Restore state
            self.ctx.depth_mask = True
            self.ctx.disable(moderngl.BLEND)

        except Exception as e:
            print(f"Error rendering beam: {e}")
            import traceback
            traceback.print_exc()
            # Try to restore state on error
            try:
                self.ctx.depth_mask = True
                self.ctx.disable(moderngl.BLEND)
            except:
                pass

    def release(self):
        """Release GPU resources."""
        super().release()
        for attr in ['base_vao', 'base_vbo', 'base_nbo',
                     'yoke_vao', 'yoke_vbo', 'yoke_nbo',
                     'head_vao', 'head_vbo', 'head_nbo',
                     'lens_vao', 'lens_vbo', 'lens_nbo',
                     'beam_vao', 'beam_vbo', 'beam_abo', 'beam_program']:
            obj = getattr(self, attr, None)
            if obj:
                obj.release()


class WashRenderer(FixtureRenderer):
    """Renderer for wash/flood fixtures."""

    BODY_COLOR = (0.12, 0.12, 0.15)

    def __init__(self, ctx: moderngl.Context, fixture_data: Dict[str, Any]):
        super().__init__(ctx, fixture_data)
        self._create_geometry()

    def _create_geometry(self):
        """Create wash fixture body and lens."""
        self.program = self.ctx.program(
            vertex_shader=FIXTURE_VERTEX_SHADER,
            fragment_shader=FIXTURE_FRAGMENT_SHADER
        )

        # Create main body
        body_verts, body_norms = GeometryBuilder.create_box(
            self.width, self.height, self.depth
        )

        self.vbo = self.ctx.buffer(body_verts.tobytes())
        self.nbo = self.ctx.buffer(body_norms.tobytes())
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '3f', 'in_position'), (self.nbo, '3f', 'in_normal')]
        )

        # Create lens/front emitter
        lens_width = self.width * 0.85
        lens_height = self.height * 0.85
        lens_depth = 0.02

        lens_verts, lens_norms = GeometryBuilder.create_box(
            lens_width, lens_height, lens_depth,
            center=(0, 0, self.depth / 2 + lens_depth / 2)
        )

        self.lens_vbo = self.ctx.buffer(lens_verts.tobytes())
        self.lens_nbo = self.ctx.buffer(lens_norms.tobytes())
        self.lens_vao = self.ctx.vertex_array(
            self.program,
            [(self.lens_vbo, '3f', 'in_position'), (self.lens_nbo, '3f', 'in_normal')]
        )

    def render(self, mvp: glm.mat4):
        """Render the wash fixture."""
        model = self.get_model_matrix()
        final_mvp = mvp * model

        mvp_bytes = np.array([x for col in final_mvp.to_list() for x in col], dtype='f4').tobytes()
        model_bytes = np.array([x for col in model.to_list() for x in col], dtype='f4').tobytes()

        self.program['mvp'].write(mvp_bytes)
        self.program['model'].write(model_bytes)

        # Render body
        self.program['base_color'].value = self.BODY_COLOR
        self.program['emissive_color'].value = (0.0, 0.0, 0.0)
        self.program['emissive_strength'].value = 0.0
        self.vao.render(moderngl.TRIANGLES)

        # Render lens with color
        color = self.get_color()
        dimmer = self.get_dimmer()

        # Add white channel
        white = self.dmx_values.get('white', 0) / 255.0
        color = (
            min(1.0, color[0] + white),
            min(1.0, color[1] + white),
            min(1.0, color[2] + white)
        )

        emissive = (color[0] * dimmer, color[1] * dimmer, color[2] * dimmer)

        self.program['base_color'].value = (0.15, 0.15, 0.15)
        self.program['emissive_color'].value = emissive
        self.program['emissive_strength'].value = 1.0

        self.lens_vao.render(moderngl.TRIANGLES)

    def release(self):
        """Release GPU resources."""
        super().release()
        if hasattr(self, 'lens_vao') and self.lens_vao:
            self.lens_vao.release()
        if hasattr(self, 'lens_vbo') and self.lens_vbo:
            self.lens_vbo.release()
        if hasattr(self, 'lens_nbo') and self.lens_nbo:
            self.lens_nbo.release()


class PARRenderer(FixtureRenderer):
    """Renderer for PAR can fixtures (default type)."""

    BODY_COLOR = (0.1, 0.1, 0.12)

    def __init__(self, ctx: moderngl.Context, fixture_data: Dict[str, Any]):
        super().__init__(ctx, fixture_data)
        self._create_geometry()

    def _create_geometry(self):
        """Create PAR can body and lens."""
        self.program = self.ctx.program(
            vertex_shader=FIXTURE_VERTEX_SHADER,
            fragment_shader=FIXTURE_FRAGMENT_SHADER
        )

        # PAR can is a cylinder
        radius = min(self.width, self.height) / 2
        body_verts, body_norms = GeometryBuilder.create_cylinder(
            radius, self.depth, segments=24
        )

        self.vbo = self.ctx.buffer(body_verts.tobytes())
        self.nbo = self.ctx.buffer(body_norms.tobytes())
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '3f', 'in_position'), (self.nbo, '3f', 'in_normal')]
        )

        # Create lens (front face)
        lens_verts, lens_norms = GeometryBuilder.create_cylinder(
            radius * 0.85, 0.02, segments=24,
            center=(0, self.depth / 2 + 0.01, 0)
        )

        self.lens_vbo = self.ctx.buffer(lens_verts.tobytes())
        self.lens_nbo = self.ctx.buffer(lens_norms.tobytes())
        self.lens_vao = self.ctx.vertex_array(
            self.program,
            [(self.lens_vbo, '3f', 'in_position'), (self.lens_nbo, '3f', 'in_normal')]
        )

    def render(self, mvp: glm.mat4):
        """Render the PAR can."""
        model = self.get_model_matrix()

        # Rotate to lay horizontally (PAR typically faces forward)
        rotation = glm.rotate(glm.mat4(1.0), glm.radians(-90), glm.vec3(1, 0, 0))
        model = model * rotation

        final_mvp = mvp * model

        mvp_bytes = np.array([x for col in final_mvp.to_list() for x in col], dtype='f4').tobytes()
        model_bytes = np.array([x for col in model.to_list() for x in col], dtype='f4').tobytes()

        self.program['mvp'].write(mvp_bytes)
        self.program['model'].write(model_bytes)

        # Render body
        self.program['base_color'].value = self.BODY_COLOR
        self.program['emissive_color'].value = (0.0, 0.0, 0.0)
        self.program['emissive_strength'].value = 0.0
        self.vao.render(moderngl.TRIANGLES)

        # Render lens with color
        color = self.get_color()
        dimmer = self.get_dimmer()

        white = self.dmx_values.get('white', 0) / 255.0
        color = (
            min(1.0, color[0] + white),
            min(1.0, color[1] + white),
            min(1.0, color[2] + white)
        )

        emissive = (color[0] * dimmer, color[1] * dimmer, color[2] * dimmer)

        self.program['base_color'].value = (0.15, 0.15, 0.15)
        self.program['emissive_color'].value = emissive
        self.program['emissive_strength'].value = 1.0

        self.lens_vao.render(moderngl.TRIANGLES)

    def release(self):
        """Release GPU resources."""
        super().release()
        if hasattr(self, 'lens_vao') and self.lens_vao:
            self.lens_vao.release()
        if hasattr(self, 'lens_vbo') and self.lens_vbo:
            self.lens_vbo.release()
        if hasattr(self, 'lens_nbo') and self.lens_nbo:
            self.lens_nbo.release()


class FixtureManager:
    """Manages all fixture renderers and coordinates updates."""

    def __init__(self, ctx: moderngl.Context):
        """
        Initialize fixture manager.

        Args:
            ctx: ModernGL context
        """
        self.ctx = ctx
        self.fixtures: Dict[str, FixtureRenderer] = {}

    def update_fixtures(self, fixtures_data: List[Dict[str, Any]]):
        """
        Update fixtures from TCP message.

        Args:
            fixtures_data: List of fixture dictionaries from TCP
        """
        # Track which fixtures we've seen
        seen_fixtures = set()

        for fixture_data in fixtures_data:
            name = fixture_data.get('name', '')
            if not name:
                continue

            seen_fixtures.add(name)

            # Check if fixture already exists
            if name in self.fixtures:
                existing = self.fixtures[name]
                # Check if fixture has changed significantly
                if (existing.position != fixture_data.get('position') or
                    existing.rotation != fixture_data.get('rotation', 0)):
                    # Recreate fixture
                    existing.release()
                    self.fixtures[name] = self._create_fixture(fixture_data)
            else:
                # Create new fixture
                self.fixtures[name] = self._create_fixture(fixture_data)

        # Remove fixtures that no longer exist
        for name in list(self.fixtures.keys()):
            if name not in seen_fixtures:
                self.fixtures[name].release()
                del self.fixtures[name]

        print(f"FixtureManager: {len(self.fixtures)} fixtures loaded")
        for name, fix in self.fixtures.items():
            extra_info = ""
            if isinstance(fix, MovingHeadRenderer):
                # Show pan/tilt channel mapping for moving heads
                ch_map = fix.channel_mapping
                pan_ch = [k for k, v in ch_map.items() if v == 'pan']
                tilt_ch = [k for k, v in ch_map.items() if v == 'tilt']
                dimmer_ch = [k for k, v in ch_map.items() if v == 'dimmer']
                color_ch = [k for k, v in ch_map.items() if v == 'color_wheel']
                cw_count = len(fix.color_wheel) if hasattr(fix, 'color_wheel') else 0
                extra_info = f", pan={pan_ch}, tilt={tilt_ch}, dim={dimmer_ch}, color={color_ch}, wheel_colors={cw_count}"
            print(f"  - {name}: type={fix.__class__.__name__}, U{fix.universe}@{fix.address}{extra_info}")

    def _create_fixture(self, fixture_data: Dict[str, Any]) -> FixtureRenderer:
        """
        Create appropriate renderer for fixture type.

        Args:
            fixture_data: Fixture data dictionary

        Returns:
            FixtureRenderer instance
        """
        fixture_type = fixture_data.get('fixture_type', 'PAR')

        if fixture_type == 'MH':
            return MovingHeadRenderer(self.ctx, fixture_data)
        elif fixture_type == 'BAR':
            return LEDBarRenderer(self.ctx, fixture_data)
        elif fixture_type == 'SUNSTRIP':
            return SunstripRenderer(self.ctx, fixture_data)
        elif fixture_type == 'WASH':
            return WashRenderer(self.ctx, fixture_data)
        else:  # PAR or unknown
            return PARRenderer(self.ctx, fixture_data)

    def update_dmx(self, universe: int, dmx_data: bytes):
        """
        Update fixtures with new DMX data.

        Args:
            universe: Universe number
            dmx_data: 512 bytes of DMX data
        """
        updated_count = 0
        for fixture in self.fixtures.values():
            if fixture.universe == universe:
                fixture.update_dmx(dmx_data)
                updated_count += 1

        # Debug: log first few DMX updates
        if not hasattr(self, '_dmx_log_count'):
            self._dmx_log_count = 0
        if self._dmx_log_count < 5 and updated_count > 0:
            self._dmx_log_count += 1
            # Show first 20 channels
            ch_preview = [dmx_data[i] for i in range(min(20, len(dmx_data)))]
            print(f"DMX U{universe}: {updated_count} fixtures, ch1-20: {ch_preview}")

    def render(self, mvp: glm.mat4):
        """
        Render all fixtures.

        Args:
            mvp: View-projection matrix
        """
        for fixture in self.fixtures.values():
            fixture.render(mvp)

    def get_fixture(self, name: str) -> Optional[FixtureRenderer]:
        """Get fixture by name."""
        return self.fixtures.get(name)

    def release(self):
        """Release all GPU resources."""
        for fixture in self.fixtures.values():
            fixture.release()
        self.fixtures.clear()
