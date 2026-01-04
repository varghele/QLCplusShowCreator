# Fixture Renderer Coordinate System Reference

## Global Stage Coordinate System

- **X axis**: Stage left/right (positive X = stage right)
- **Y axis**: Toward audience (front of stage)
- **Z axis**: Up (vertical, toward sky)

```
        +Z (up)
         |
         |
         |_______ +Y (toward audience)
        /
       /
      +X (stage right)
```

---

## Moving Head Fixture

### Physical Description
- Base plate (sits on truss/floor)
- Yoke arms (hold the head, rotate with pan around Z axis)
- Head (rotates with tilt, contains lens)
- Lens (where light exits)

### Internal Coordinate System

**Pan Rotation:**
- Rotates around **Z axis** (vertical)
- Pan DMX 0: 0° rotation, head faces +X direction
- Pan DMX 255: pan_max degrees rotation (from fixture config)
- Positive rotation is CCW when viewed from above (+Z)

**Tilt Rotation:**
- Rotates around **Y axis** (in yoke's local space, perpendicular to forward)
- Tilt DMX 0: 0° rotation, beam points forward (+X in yoke space)
- Tilt DMX 255: tilt_max degrees rotation (from fixture config)
- Rotation direction: increasing tilt moves beam from forward (+X) toward up (+Z)

**Beam Direction Examples (at Pan=0):**

| Tilt | Beam Points |
|------|-------------|
| 0°   | +X (forward) |
| 90°  | +Z (straight up) |
| 180° | -X (backward) |

---

## Sunstrip Fixture

### Physical Description
- Linear bar with multiple lamp segments
- Light exits perpendicular to the bar length

### Internal Coordinate System
- **Bar extends along**: X axis
- **Lamps/light face**: +Z direction

```
   Lamps face +Z (up)
        ^
        |
   [====|====]  <-- bar extends along X axis
```

---

## LED Bar Fixture

### Physical Description
- Linear bar with LED segments
- Similar to sunstrip but typically RGB LEDs

### Internal Coordinate System
- **Bar extends along**: X axis (same as Sunstrip)
- **LEDs face**: +Z direction

```
   LEDs face +Z (up)
        ^
        |
   [====|====]  <-- bar extends along X axis
```

---

## PAR Can Fixture

### Physical Description
- Cylindrical can
- Lens at front

### Internal Coordinate System
- **Cylindrical body extends along**: Z axis
- **Lens/beam faces**: +Z direction

```
     Lens
      ___
     /   \  --> +Z (beam direction)
    |     |
    |_____|
      Body along Z axis
```

---

## Wash Fixture

### Physical Description
- Similar to PAR but typically with multiple LEDs
- Flatter profile than PAR

### Internal Coordinate System
- **Body lies in**: X-Y plane
- **Lens/beam faces**: +Z direction

```
    +Z (beam direction)
     ^
     |
   _____
  |     |  <-- body in X-Y plane
  |_____|
```

---

## Coordinate Axes Colors (for debugging)
- **X axis**: Red
- **Y axis**: Blue
- **Z axis**: Green

---

## Summary Table

| Fixture     | Body/Bar Orientation | Beam/Light Direction |
|-------------|---------------------|----------------------|
| Moving Head | Base in X-Y plane   | Varies with Pan/Tilt |
| Sunstrip    | Along X axis        | +Z                   |
| LED Bar     | Along X axis        | +Z                   |
| PAR Can     | Along Z axis        | +Z                   |
| Wash        | In X-Y plane        | +Z                   |

---

## Notes
- Internal coordinate system = fixture's local coordinate system before stage placement transforms
- Stage placement orientation rotates the fixture around Z axis (yaw)
- All static fixtures (non-moving head) have beams facing +Z in their local coordinate system
