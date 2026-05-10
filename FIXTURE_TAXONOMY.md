# Fixture Taxonomy & Visualizer Building-Block Design

Research doc for designing a complete fixture-rendering system that covers **every QLC+ fixture type**, not just the six we currently handle.

> **Status:** Research + design sketch. No code changes proposed yet — this is the source of truth for the implementation plan that follows.
>
> **Sources:** QLC+ schema (`http://www.qlcplus.org/FixtureDefinition`), the upstream library at `mcallegari/qlcplus/resources/fixtures/`, verification against the 4 `.qxf` files in `custom_fixtures/`, and a full read of `visualizer/renderer/fixtures.py` + `utils/fixture_utils.py`. Fixture counts in §2 are estimates from the upstream library — the absolute Type list and channel-preset names are authoritative.

---

## 1. Where we are today

### 1.1 The six-string enum

`utils/fixture_utils.py::determine_fixture_type` collapses every QLC+ fixture into one of:

| Tag | Renderer | What it covers today |
|---|---|---|
| `MH` | `MovingHeadRenderer` | Pan/tilt + dimmer + RGB-or-color-wheel + gobo + prism + focus, all assumed present |
| `BAR` | `LEDBarRenderer` | Single RGB(W) source spread across a bar body |
| `PIXELBAR` | `PixelBarRenderer` | 1×N RGBW cells, individually addressable |
| `SUNSTRIP` | `SunstripRenderer` | 1×N dimmer-only cells |
| `WASH` | `WashRenderer` | Stationary RGB(W) wash, no movement |
| `PAR` | `PARRenderer` | Default fallback — RGB(W) with optional dimmer |

### 1.2 Five downstream consumers of that enum

Any extension of the enum has to be threaded through every one of these:

| Consumer | File | What it switches on |
|---|---|---|
| Renderer dispatch | `visualizer/renderer/fixtures.py:3640` (`FixtureManager._create_fixture`) | Picks the right `FixtureRenderer` subclass |
| 2D top-down icon | `gui/stage_items.py:115` (`FixtureItem.paint`) | Picks the symbol shape on the Stage tab |
| 3D orientation preview | `gui/dialogs/orientation_dialog.py:201,1329` | Picks the geometry in the OrientationDialog |
| Group constraints | `config/models.py::Group.fixture_types` | Restricts a group to certain types |
| QXF parsing branches | `utils/tcp/protocol.py:276–523` (`build_fixtures_payload`) | Refines `BAR → PIXELBAR / WASH / SUNSTRIP` based on channel analysis |

### 1.3 Renderer payload (what reaches the visualizer)

`utils/tcp/protocol.py::build_fixtures_payload` assembles per-fixture:

- `position {x,y,z}`, `orientation {mounting,yaw,pitch,roll}`
- `physical {width,height,depth}`
- `layout {width,height}` (cell grid)
- `channel_mapping {dmx_channel_offset → semantic_function}`
- `pixel_segments [{channels, red, green, blue, white}, ...]` (per-mode)
- `beam_angle` (degrees), `lumens` (estimated from `power_consumption × LED-or-halogen efficiency`)
- `fixture_type` (the six-string enum)

### 1.4 Gaps already known

- **Moving-head bar** (4–10 moving heads on one chassis with independent pan/tilt) — `MovingHeadRenderer` is single-head only.
- **Moving wash without gobo** (e.g. Martin MAC Aura) — `MovingHeadRenderer` assumes gobo+prism+focus; `WashRenderer` is stationary. Currently classified `MH` and rendered with a fictional gobo subsystem.
- Non-light fixtures (hazers, smoke, fan, laser, scanner, strobe, effect, flower) — all collapse to `PAR` and render as a generic point.

---

## 2. The QLC+ Type landscape

Every `.qxf` declares one of a fixed enumeration in its `<Type>` element. Approximate counts in the upstream library:

| Type | ~Count | Has light? | Has movement? | Render concept |
|---|---|---|---|---|
| **Moving Head** | ~1700 | Yes | Pan + Tilt | Beam cone from a yoke head |
| **Color Changer** | ~1300 | Yes | No | Single-source RGB(W) wash (PAR-class) |
| **LED Bar (Beams)** | ~350 | Yes | No | 1×N cells with beam optics |
| **LED Bar (Pixels)** | ~250 | Yes | No | 1×N cells, no beam optics (sunstrip-style) |
| **Dimmer** | ~250 | Yes (via load) | No | N independent dimmer outputs (driving conventional lamps) |
| **Scanner** | ~150 | Yes | Pan + Tilt (mirror) | Beam reflected off a moving mirror |
| **Strobe** | ~120 | Yes (pulsed) | No | Bright stationary flash output |
| **Effect** | ~120 | Yes | Sometimes | Multi-beam patterned effect lights (centipede, derby, sweeper) |
| **Laser** | ~100 | Yes (vector) | Vector scanning | Pattern + position, not a cone |
| **Hazer** | ~60 | No | No | Particle plume |
| **Smoke** | ~80 | No | No | Particle plume |
| **Flower** | ~40 | Yes | Sometimes | Multi-beam fixed-pattern (similar to Effect) |
| **Fan** | ~10 | No | No | Air movement, no visible output |
| **LED Matrix** | ~20 | Yes | No | W×H grid of pixel cells |
| **Other** | ~80 | Varies | Varies | Grab bag — video panels, accessories, oddballs |

Plus a few alias/legacy strings: `Lyre` (= Moving Head), `Color Wheel` (= Color Changer).

### 2.1 Multi-emitter fixtures (the part our current renderer mostly misses)

QLC+ marks multi-emitter devices two ways:

- `<Mode><Head><Channel>N</Channel>…</Head></Mode>` — each `<Head>` lists the channel indices belonging to one logical sub-fixture.
- `<Physical><Layout Width="W" Height="H"/>` — geometric grid for cell placement.

Archetypes found in the library:

| Archetype | Layout | Heads | Examples | Currently handled? |
|---|---|---|---|---|
| Pixel-strip bar | `1×N` | N RGB(W) heads | Eurolite Bar-12, Chauvet COLORband PiX-M, Varghele LED BAR | Yes (`PIXELBAR`) |
| Sunstrip-style segment bar | `1×N` | N dimmer-only heads | Showtec Sunstrip Active | Yes (`SUNSTRIP`) |
| Pixel matrix | `W×H` (W,H>1) | W·H heads | Chauvet MotionFacade 4×4, ADJ Mega Pixel 5×5, Cameo Pixbar | **No** |
| Moving-head bar | `1×N` | N independent pan/tilt heads | Ayrton MagicBlade-R (7), GLP impression X4 Bar 10, Martin MAC Quantum Bar | **No** |
| Spider / centipede / derby | varies | N shared-base, partial-independent arms | ADJ Inno Pocket Spot, Equinox Onyx, Stairville Octagon Beam Quad | **No** |
| Multi-zone PAR | encoded by heads | Concentric or split RGBA(W/UV) zones | ADJ 12PX Hex (12), Chauvet Rogue R2X Wash (zoned ring + center) | Partial (renders as single source) |
| Hybrid bar | switchable per mode | 1 or N depending on mode | Varytec Giga Bar (3ch global ↔ 51ch per-cell) | Partial (mode-dependent) |

---

## 3. Common-denominator capability axes

Strip away fixture types and what's left is a small set of **orthogonal capabilities**. Every fixture is a point in this space.

### 3.1 Movement
- `pan` (8-bit + optional `pan_fine` 8-bit → 16-bit)
- `tilt` (same)
- `pan_speed`, `tilt_speed` (animation easing only, doesn't affect geometry)
- **Movement type** from `<Physical><Focus Type="…">`: `Head` (yoke rotates body), `Mirror` (mirror reflects beam — origin offset), `Barrel` (rotating barrel scanner), `Fixed` (no movement)
- **Per-head movement** for moving bars: each `<Head>` may carry its own pan/tilt channels

### 3.2 Color
- **Additive mixing**: RGB / RGBW / RGBA / RGBAW / RGBWAUV / RGBA+Lime
- **Subtractive mixing**: CMY (mostly arc-lamp moving heads)
- **HSL/HSI/HSV channels** (newer fixtures, e.g. Varytec Giga Bar)
- **Color wheel** (`ColorWheel` / `ColorMacro` preset): discrete positions + optional rainbow rotation at the channel ends
- **CTO/CTB/CTC** color temperature correction
- **UV emitter** (render as deep violet, optionally with bloom)

### 3.3 Intensity & beam shaping
- `dimmer` (master intensity)
- `strobe` (rate + open/closed) — sometimes a sub-range of a `Shutter` channel via `Preset="StrobeSlowToFast"`
- `iris` (aperture diameter)
- `frost` (beam softness / haze layer)
- `zoom` (`<Lens DegreesMin Max>` — when `Min < Max` it's a zoom range; when `Min == Max` fixed)
- `focus` (sharpness — affects gobo edge, not cone width)

### 3.4 Pattern / image
- `gobo_static` (discrete positions)
- `gobo_rotation` (continuous rotation independent of position)
- `gobo_shake` (positions wobbling in place)
- `animation_wheel` (continuous moving texture overlay)
- `prism` (multiplies beam — facet count typically in `Res1` attribute, e.g. `Res1="3"`)
- `prism_rotation`
- `gobo2` (some fixtures have two gobo wheels)

### 3.5 Multi-emitter shape
- `single_cell_single_head` — basic PAR
- `single_head_multi_cell` — pixel bar (1×N), pixel matrix (W×H)
- `multi_head_shared_base` — moving bar, spider light
- `multi_head_independent` — every head has its own pan/tilt

### 3.6 Non-light outputs
- `particle_emitter` — hazer, smoke, fog, snow, bubble, flame (subtypes of "Smoke" / "Effect")
- `fan` — air movement, no visual (could optionally render dust or smoke deflection)
- `laser_vector` — vector pattern playback (DMX-controlled ILDA)
- `laser_xy` — X/Y position + color, treated like a moving spot but with vector beam

### 3.7 Auxiliary / non-visual
- Reset, lamp on/off, pan/tilt invert (control-only)
- Sound-active toggles
- Macro/program selectors (bake-in choreography — render as "doing something" rather than locking the beam)
- `NoFunction` / virtual channels (ignore)

---

## 4. Outliers (need bespoke handling)

These don't fit the "render as a beam cone" model:

| Outlier | What it is | Render strategy |
|---|---|---|
| **Generic RGB Panel / Video Wall** | Hundreds of channels driving a W×H pixel grid for video playback (Type: `Other` / `LED Matrix`) | 2D textured quad, not discrete beams |
| **Pangolin / ILDA Laser bridges** | One channel selects from a library of full vector animations | Placeholder cone or generic "laser pattern" symbol — we cannot know the animation |
| **Pixel Bubbles / LED Mesh / Fiber-optic ceilings** | Non-planar geometry (Type: `Other` / `Color Changer`) | User-placed point cloud, not encoded in `<Physical>` |
| **DMX-controlled cameras / follow-spots** | Pan/tilt-like channels but no visible output (Type: `Other`) | Render as a tracking gizmo, no beam |
| **Bubble / Snow / Flame machines** | Non-uniform 3D particle output (Type: `Smoke` / `Effect`) | Particle plume with type-specific colour/density |
| **Multi-mode "all-things-to-all-people" fixtures** | E.g. Varytec Giga Bar — 7 modes, 3ch ↔ 51ch on the same hardware | Visualizer commits to the patched mode; cannot be mode-agnostic |
| **Fixtures referencing custom SVG gobos** | `Res1="vendor/gobo00123.svg"` pointing at QLC+ resource files | Optional: load SVGs from `resources/gobos/` and project them. Fallback: textured cone |
| **Fixtures with `VirtualNothing` / `NoFunction` channels** | DMX-burning channels with no effect | Ignore |

---

## 5. File-format quirks to bake into the parser

Not new findings, but worth pinning down so the new model handles them:

- **Namespace required**: `xmlns="http://www.qlcplus.org/FixtureDefinition"`. `utils/fixture_utils.py` already strips it correctly.
- **Modes have their own channel ordering**: `<Mode><Channel Number="0">Pan</Channel>…</Mode>` references global `<Channel Name="…"/>` definitions. A fixture has 1..N modes.
- **Modes may override `<Physical>`**: mode-level merges on top of fixture-level. `build_fixtures_payload` doesn't currently handle this — Varytec Giga Bar's 48ch and 51ch modes carry their own `<Physical>` block with different `<Layout>`.
- **`<Head>` blocks live inside `<Mode>`**, not inside `<Channel>`. The integer is the channel index *within the mode*, not a global ID.
- **`<Physical><Lens DegreesMin DegreesMax>`**: when `Min == Max`, fixed cone. When different, zoom range. When both `0`, no beam optic — render as a flat-emitting bar (current `BAR`/`SUNSTRIP` already does this).
- **`<Physical><Focus Type="Head|Mirror|Barrel|Fixed">`**: tells the renderer *where the rotation centre is* — Head rotates body, Mirror reflects (origin offset), Barrel = scanner, Fixed = stationary.
- **Channel `Preset` is the ground truth**, not the channel name. Switch on the preset enumeration listed in §3, not on string-matching channel names. (The current `determine_fixture_type` does some of this already but mixes name and preset matching.)
- **`Res1` semantics depend on context**: `#RRGGBB` for color macros, SVG path for gobos, integer facet count for prisms.
- **`<Capability>` ranges** carry their own `Preset` (e.g. `StrobeSlowToFast` for a sub-range of a shutter channel). The renderer needs to read capability presets, not just channel presets, to know what a mid-range DMX value means.
- **`Group Byte="0"` / `Byte="1"`**: legacy classification (coarse / fine companion). Both `Group` and `Preset` may be present; newer fixtures use `Preset` only, older ones use `Group` only. Both need supporting.

---

## 6. Proposed building-block model

### 6.1 Design principle — composition over inheritance

The current code subclasses `FixtureRenderer` per type. That works for 6 types; it doesn't scale to the 15-Type matrix above. Six subclasses already share a lot (beam helpers, geometry, axes, mounting), and the per-type subclasses bake assumptions ("an MH always has a gobo wheel") that block legitimate variants ("a moving wash has no gobo").

The proposal: **a fixed renderer scaffolding that composes capability components**.

```
FixtureRenderer
├── Chassis (fixed: PAR / BAR / PANEL / MOVING_YOKE / SCANNER / EFFECT / PARTICLE / LASER / OTHER)
├── Movement?       (None | YokeMovement | MirrorMovement | BarrelMovement)
├── ColorMixing?    (None | RGBMixing | RGBWMixing | RGBAWMixing | RGBWAUVMixing | CMYMixing | HSLMixing)
├── ColorWheel?     (None | discrete-positions + rotation)
├── Dimmer?         (None | DimmerCapability)
├── Strobe?         (None | StrobeCapability)
├── BeamShape?      (None | FixedConeBeam(angle) | ZoomBeam(min,max) | NoOptics)
├── BeamModifiers   ([] | [Iris, Frost, Focus])
├── Pattern?        (None | GoboWheel | Gobo2Wheel | AnimationWheel)
├── Prism?          (None | PrismCapability(facets))
└── Emitter         (PointEmitter | CellArray(W,H) | MultiHead([HeadDescriptor]) | ParticlePlume | LaserVector)
```

The `Chassis` is the body shape (what the user sees as a 2D icon and as a 3D mesh shell). The `Emitter` is what produces the visible output. Capabilities stack onto the emitter — a `MultiHead` chassis with `YokeMovement` per head + `RGBWMixing` + `GoboWheel` is a moving-head bar.

This fixes the two known gaps directly:
- **Moving-head bar** = `MOVING_YOKE` chassis × `MultiHead([HeadDescriptor with YokeMovement, RGBWMixing, GoboWheel])`
- **Moving wash** = `MOVING_YOKE` chassis × `PointEmitter` × `YokeMovement` × `RGBWMixing` × no `GoboWheel`

### 6.2 Capability detection

Replace the imperative `determine_fixture_type` cascade with a **capability-detection pass** that reads each channel's `Preset` and each capability's `Preset` and produces a `FixtureCapabilities` dataclass:

```python
@dataclass
class FixtureCapabilities:
    chassis: Chassis                 # body shape — derived from <Type> + heuristics
    qlc_type: str                    # raw <Type> string for fallback / diagnostics

    # Movement
    movement: Optional[Movement]     # YokeMovement, MirrorMovement, BarrelMovement, or None
    pan_max_deg: float               # 0 if no movement
    tilt_max_deg: float

    # Color
    color_mixing: Optional[ColorMixing]    # RGB / RGBW / RGBA / RGBAW / RGBWAUV / CMY / HSL
    color_wheel: Optional[ColorWheel]      # list of (dmx_value, name, hex) — coexists with color_mixing

    # Intensity
    has_dimmer: bool
    has_strobe: bool
    has_iris: bool
    has_frost: bool
    has_focus: bool

    # Beam
    beam_min_deg: float              # from <Lens DegreesMin>
    beam_max_deg: float              # from <Lens DegreesMax>; equal to min = fixed cone
    has_zoom: bool                   # = beam_min_deg != beam_max_deg

    # Pattern
    gobo_wheel: Optional[GoboWheel]
    gobo2_wheel: Optional[GoboWheel]
    animation_wheel: bool
    prism: Optional[Prism]           # carries facet count

    # Emitter shape
    emitter: Emitter                 # PointEmitter | CellArray | MultiHead | ParticlePlume | LaserVector

    # Physical
    body_dims_m: Tuple[float, float, float]  # width, height, depth
    layout: Tuple[int, int]                  # cell grid (W, H)
    lumens_estimate: float
```

### 6.3 The renderer base + components

```python
class FixtureRenderer:
    """Owns geometry (chassis shell + axes overlay), position, orientation,
    and a list of CapabilityComponents that drive what gets rendered each frame."""

    def __init__(self, ctx, fixture_data, capabilities: FixtureCapabilities):
        self.ctx = ctx
        self.position, self.orientation = ...
        self.chassis = ChassisGeometry.for_chassis(capabilities.chassis, capabilities.body_dims_m)

        # Build the component pipeline from capabilities. Order matters for render
        # (movement first to set the local frame, then beam, then patterns).
        self.components: list[FixtureComponent] = []
        if capabilities.movement:
            self.components.append(MovementComponent(capabilities.movement, ...))
        if capabilities.color_mixing or capabilities.color_wheel:
            self.components.append(ColorComponent(capabilities.color_mixing, capabilities.color_wheel))
        if capabilities.has_dimmer:
            self.components.append(DimmerComponent())
        if capabilities.has_strobe:
            self.components.append(StrobeComponent())
        if capabilities.beam_max_deg > 0:
            self.components.append(BeamComponent(
                min_deg=capabilities.beam_min_deg,
                max_deg=capabilities.beam_max_deg,
                modifiers=[Iris() if capabilities.has_iris else None,
                           Frost() if capabilities.has_frost else None,
                           Focus() if capabilities.has_focus else None],
            ))
        if capabilities.gobo_wheel:
            self.components.append(GoboComponent(capabilities.gobo_wheel))
        if capabilities.prism:
            self.components.append(PrismComponent(capabilities.prism))

        # Emitter is structural — it expands the render loop into 1 / N / W*H passes.
        self.emitter = EmitterRunner.for_emitter(capabilities.emitter, self.components)

    def update_dmx(self, dmx_data: bytes):
        """Each component reads the channels it cares about from dmx_data
        via the channel_mapping and updates its own state."""
        for c in self.components:
            c.update_dmx(dmx_data, self.channel_mapping)

    def render(self, mvp):
        self.chassis.render(mvp, self.get_model_matrix())
        self.emitter.render(mvp, self.get_model_matrix(), self.components)
```

```python
class FixtureComponent(ABC):
    """A capability that reads DMX and contributes to rendering. Order in
    the components list determines render order (and uniform-set order)."""

    @abstractmethod
    def update_dmx(self, dmx_data: bytes, channel_mapping: dict): ...

    def setup_uniforms(self, program, ctx):
        """Optional: write component-state uniforms to the shader program
        before the draw call. e.g. ColorComponent writes `beam_color`."""

    def transform_local_frame(self, model: glm.mat4) -> glm.mat4:
        """Optional: contribute to the local frame transform.
        MovementComponent applies pan/tilt rotations here."""
        return model
```

```python
class EmitterRunner(ABC):
    """Expands one logical fixture into 1/N/W*H render passes.
    PointEmitter      → one beam from the chassis origin
    CellArray(W, H)   → W*H beams from cell positions on the chassis
    MultiHead(heads)  → N sub-fixture renders, each with own movement
    ParticlePlume     → particle system (haze/smoke/fog/snow/bubble)
    LaserVector       → vector pattern (X/Y position + color)
    """
    @abstractmethod
    def render(self, mvp, model_matrix, components): ...
```

### 6.4 Chassis geometry library

A small fixed library of body meshes (this *is* a per-type concern — it's what the user sees as fixture shape):

| Chassis | 3D mesh | 2D icon |
|---|---|---|
| `PAR` | Cylinder + lens | Circle |
| `BAR` | Long thin box | Elongated rectangle |
| `PANEL` | Flat box (W×H aspect) | Square / aspect rect |
| `MOVING_YOKE` | Yoke + rotating head | Circle + direction triangle |
| `SCANNER` | Box + protruding mirror | Box + arrow |
| `EFFECT` | Box (centipede / derby variants) | Hexagon / star |
| `PARTICLE` | Box | Cloud icon |
| `LASER` | Box | Triangle pointing forward |
| `OTHER` | Box (placeholder) | Question-mark square |

Multi-head chassis (`MOVING_YOKE` with N heads, `BAR` with N pixels, `PANEL` with W×H pixels) compose: a base chassis + N sub-chassis at offsets.

---

## 7. Migration map — current → proposed

| Today's class | Today's `fixture_type` | Proposed components |
|---|---|---|
| `PARRenderer` | `PAR` | Chassis=`PAR`, Emitter=`PointEmitter`, ColorMixing=`RGB(W)`, Dimmer, optional Strobe |
| `WashRenderer` | `WASH` | Chassis=`PAR`, Emitter=`PointEmitter`, ColorMixing=`RGB(W)`, Dimmer, Strobe, BeamShape=`FixedCone(wide)` |
| `LEDBarRenderer` | `BAR` | Chassis=`BAR`, Emitter=`PointEmitter` *(or `CellArray(N,1)` with shared color)*, ColorMixing=`RGBW`, Dimmer |
| `PixelBarRenderer` | `PIXELBAR` | Chassis=`BAR`, Emitter=`CellArray(N,1)`, per-cell ColorMixing=`RGBW`, optional shared Dimmer |
| `SunstripRenderer` | `SUNSTRIP` | Chassis=`BAR`, Emitter=`CellArray(N,1)`, per-cell `Dimmer` only, BeamShape=`NoOptics` |
| `MovingHeadRenderer` | `MH` | Chassis=`MOVING_YOKE`, Emitter=`PointEmitter`, Movement=`YokeMovement`, ColorMixing OR ColorWheel, Dimmer, Strobe, BeamShape=`FixedCone | ZoomBeam`, optional Gobo, Prism, Iris, Frost, Focus |

### 7.1 New types unlocked by the model (no new renderer subclasses)

| New fixture | Composition | `<Type>` |
|---|---|---|
| Moving wash (no gobo) | `MOVING_YOKE` + `YokeMovement` + `RGBW` + `Dimmer` + `ZoomBeam` | Moving Head |
| Moving-head bar | `MOVING_YOKE` + `MultiHead([{YokeMovement, RGBW, GoboWheel}, …])` | Moving Head (with `<Head>` blocks) |
| Pixel matrix | `PANEL` + `CellArray(W, H)` + per-cell `RGBW` | LED Matrix / Color Changer |
| Scanner | `SCANNER` + `MirrorMovement` + `ColorWheel` + `GoboWheel` + `FixedCone` | Scanner |
| Strobe | `PAR` + `Dimmer` + `Strobe` (no color, or simple white) | Strobe |
| Hazer / Smoke / Fog | `PARTICLE` + `ParticlePlume` (density-driven) | Hazer / Smoke |
| Fan | `OTHER` + (no emitter — debug-only render) | Fan |
| Laser (vector) | `LASER` + `LaserVector` (color + pattern from DMX) | Laser |
| Effect / Flower / Centipede | `EFFECT` + `MultiHead([fixed-direction beams])` + shared color | Effect / Flower |
| Multi-zone PAR | `PAR` + `CellArray(N, 1)` (zones) + per-cell `RGBA(W/UV)` | Color Changer |
| Generic Dimmer pack | `OTHER` + `MultiHead([{Dimmer}, …])` driving placeholder lamp icons | Dimmer |
| Video panel | `PANEL` + `CellArray(W, H)` + per-cell `RGB` (high cell count) | LED Matrix / Other |

The critical observation: **the dispatch from `<Type>` becomes a capability-detection pass, not a `if/elif` cascade**. Six subclasses become one renderer + a component registry. New fixture archetypes unlock by adding component combinations, not by adding subclasses.

### 7.2 Touchpoints in the rest of the codebase

The five downstream consumers of the six-string enum (§1.2) all need to be ported:

| Consumer | Today | Proposed |
|---|---|---|
| `FixtureManager._create_fixture` | `if fixture_type == 'MH': …` | `FixtureRenderer(ctx, fixture_data, capabilities)` — single class, components vary |
| `FixtureItem.paint` | `if fixture_type == 'PAR': drawEllipse… elif 'BAR': drawRect…` | Switch on `Chassis`; same fixed library of 2D icons (§6.4) |
| `OrientationDialog` 3D preview | Same six-string switch | Switch on `Chassis` |
| `Group.fixture_types` | List of six-strings | List of `Chassis` *or* a richer capability filter (e.g. `requires=[Movement, Gobo]`) |
| `build_fixtures_payload` | Cascade of `result['fixture_type'] = …` reassignments | One `detect_capabilities(qxf_data, mode_name) → FixtureCapabilities` call |

The `Chassis` enum (PAR / BAR / PANEL / MOVING_YOKE / SCANNER / EFFECT / PARTICLE / LASER / OTHER) **replaces the six-string `fixture_type`** as the cross-cutting tag. The `FixtureCapabilities` dataclass carries everything the renderer/icon/preview need to know beyond that.

---

## 8. Open questions for implementation

These need user decisions before the implementation plan can be ordered:

1. **Backwards compatibility of `Configuration` YAML.** `Fixture.type` is persisted as one of the six strings. If we replace it with a `Chassis` enum + `Capabilities`, do we (a) migrate the YAML on load, (b) keep `type` as a derived/cached field, or (c) version-gate and ask the user to re-import old configs?

2. **Renderer scope of `Chassis = OTHER`.** Render as a placeholder box (debug-friendly), or hide entirely? Affects how Dimmer packs and Fans look in the visualizer.

3. **Particle emitters in OpenGL.** A real haze/smoke render needs a particle system or volumetric shader. Acceptable v1 = stylized icon + density indicator above the fixture; v2 = actual particles. Which one for first cut?

4. **Laser rendering.** Real ILDA vector playback is way out of scope. Acceptable v1 = a coloured cone like a spot, with a "laser" label. Or render a small set of canned patterns (lines, fan, grid) when capabilities indicate `LaserVector`?

5. **Moving-head bars and per-head pan/tilt.** QLC+ `<Head>` blocks specify channel groupings but not 3D head positions. Do we (a) infer head positions from `<Layout Width=N Height=1>` (linear N-position bar), (b) require manual per-head offset configuration, or (c) start with shared pan/tilt for v1 and add per-head in v2?

6. **Gobo/animation SVG resources.** QLC+ ships `resources/gobos/*.svg`. Do we (a) bundle them with the visualizer, (b) load on demand from a configurable QLC+ install path, or (c) keep the current 7-pattern hardcoded set and ignore SVG references?

7. **Mode-level `<Physical>` overrides.** `build_fixtures_payload` doesn't currently merge mode-specific `<Physical>` blocks. Fix as part of capability-detection rewrite, or punt?

8. **`Chassis` granularity.** Is a 9-value `Chassis` enum the right level, or do we want finer divisions (e.g. `MOVING_YOKE_BEAM` vs `MOVING_YOKE_SPOT` vs `MOVING_YOKE_WASH` for stylized 3D differences)? Finer = more icon work, less inference.

9. **Custom-fixture override hooks.** Some fixtures (the user's `Varghele-LED-BAR`, hybrid bars) may want hand-tuned capability overrides that survive QXF re-parsing. Where do these live — a sidecar YAML, a section of the user config, or a per-fixture override field on `Fixture`?
