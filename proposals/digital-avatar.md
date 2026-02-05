# Digital Avatar from LED Matrix Headshots

## Proposal: Low-Resolution Avatar Generation

### The Idea

Capture multiple headshots at 64x32 resolution using the LED Portal system, then use these to generate an animated digital avatar. The intentionally low resolution creates a pixel-art aesthetic that sidesteps the "uncanny valley" - our brains don't expect photorealism from 2,048 pixels.

### Why This Might Work

| Challenge with HD Avatars | How 64x32 Helps |
|---------------------------|-----------------|
| Uncanny valley from "almost real" faces | Clearly stylized - reads as pixel art |
| Subtle expression errors feel wrong | Limited pixels = exaggerated, readable expressions |
| Lighting inconsistencies are jarring | Reduced color depth hides imperfections |
| High compute requirements | Tiny images = fast processing |

**Aesthetic reference**: Think Commodore 64 portraits, early Game Boy Camera, or modern pixel art games like Celeste.

---

## Capture Requirements

### Minimum Viable Dataset: 25-50 Images

**Angles (5 positions):**
- Front facing
- 3/4 left (~45°)
- 3/4 right (~45°)
- Slight up tilt
- Slight down tilt

**Expressions (5-10 per angle):**
- Neutral
- Smile (closed mouth)
- Smile (open mouth)
- Raised eyebrows (surprise)
- Furrowed brows (concern/focus)
- Eyes closed
- Speaking poses (mouth shapes: A, E, O, closed)

**Calculation:**
- 5 angles × 5 expressions = **25 minimum**
- 5 angles × 10 expressions = **50 recommended**

### Enhanced Dataset: 100-200 Images

For smoother animations and more expression range:
- Add intermediate angles (15° increments)
- Add more expression intensities (slight smile → big smile)
- Capture with different LED matrix brightness levels
- Include some motion blur frames for transitions

### For Machine Learning Approaches: 500+ Images

If training a generative model:
- Capture video sequences, extract frames
- Multiple sessions across different days
- Various clothing/accessories (glasses on/off, hat, etc.)

---

## Proposed Capture Workflow

### 1. Add Capture Mode to LED Portal

```
New keyboard command: 'a' = Avatar capture mode
- Prompts for pose name ("front_neutral", "left_smile", etc.)
- Captures burst of 5 frames, keeps sharpest
- Auto-saves with structured naming
- Shows pose checklist on terminal
```

### 2. Capture Session (~30 minutes)

```
avatar_captures/
├── front/
│   ├── front_neutral_001.bmp
│   ├── front_smile_001.bmp
│   └── ...
├── left_45/
│   ├── left_45_neutral_001.bmp
│   └── ...
└── session_metadata.json
```

### 3. Review and Curate

- Display all captures in grid
- Mark best versions of each pose
- Identify gaps (missing expressions)

---

## Software Libraries for Avatar Generation

### Tier 1: Simple Approaches (Start Here)

| Library | Purpose | Why Use It |
|---------|---------|------------|
| **Pillow (PIL)** | Image manipulation | Blend between poses, create sprite sheets |
| **NumPy** | Array operations | Fast pixel math for morphing |
| **OpenCV** | Already using | Face detection, alignment, blending |

**Approach**: Morph targets / blend shapes
- Manually tag key poses
- Blend between them based on input parameters
- Simple but effective for real-time animation

```python
# Example: Blend between neutral and smile
def blend_expressions(neutral, smile, amount):
    """amount: 0.0 = neutral, 1.0 = full smile"""
    return (neutral * (1 - amount) + smile * amount).astype(np.uint8)
```

### Tier 2: Sprite Animation

| Library | Purpose | Why Use It |
|---------|---------|------------|
| **Pygame** | 2D game engine | Sprite sheets, animation timing |
| **Arcade** | Modern 2D library | Cleaner API than Pygame |
| **Pyxel** | Retro game engine | Built for pixel art, 16-color palette |

**Approach**: Treat avatar as animated sprite
- Create sprite sheet from captures
- Define animation sequences (idle, talking, reactions)
- Real-time playback with state machine

### Tier 3: Machine Learning (Advanced)

| Library | Purpose | Complexity |
|---------|---------|------------|
| **MediaPipe** | Face mesh detection | Medium - extract 468 face landmarks |
| **dlib** | Face landmarks | Medium - 68 point face model |
| **StyleGAN3** | Generative faces | High - needs GPU, training time |
| **First Order Motion Model** | Animate from single image | High - deep learning |
| **PIFuHD** | 3D reconstruction | Very High - research grade |

**Realistic ML approach for 64x32:**
1. Use MediaPipe to extract face landmarks from captures
2. Train small neural network to map landmarks → pixel output
3. Drive avatar with live webcam landmark detection

### Tier 4: Hybrid / Creative

| Library | Purpose | Use Case |
|---------|---------|----------|
| **Stable Diffusion + ControlNet** | AI image generation | Generate new poses from text prompts |
| **Ebsynth** | Style transfer for video | Paint one frame, propagate to sequence |
| **Aseprite** (not Python) | Pixel art editor | Manual cleanup and enhancement |

---

## Recommended Starting Point

### Phase 1: Capture & Organize (Week 1)
1. Modify LED Portal to add avatar capture mode
2. Capture 50 poses (5 angles × 10 expressions)
3. Organize into structured folders

### Phase 2: Simple Blending (Week 2)
```python
# Dependencies
pip install pillow numpy opencv-python

# Core approach
- Load all captures into memory
- Build expression blending function
- Map keyboard/mouse input to expression weights
- Output blended frame to LED matrix in real-time
```

### Phase 3: Evaluate & Iterate (Week 3+)
- Does it feel like "you"?
- Is the uncanny valley avoided?
- What's missing? (probably: smooth transitions)

### Phase 4: Advanced (Optional)
- Add MediaPipe for live expression tracking
- Your real face drives your pixel avatar in real-time
- "Pixel art mirror"

---

## Quick Proof of Concept

Use the existing LED Portal snapshot feature - it already captures exactly what displays on the matrix.

```bash
# Run LED Portal
cd sandbox
python camera_feed.py

# Capture test poses:
# 1. Position your face in frame
# 2. Press 'p' for portrait mode (face fills frame better)
# 3. Press SPACE to capture (3-2-1 countdown)
# 4. Repeat for: neutral, smile, surprised

# Your captures are saved as:
#   snapshot_YYYYMMDD_HHMMSS.bmp  (64x32 color image)
#   snapshot_YYYYMMDD_HHMMSS_rgb565.bin  (raw LED data)
```

**That's it.** No phone, no manual resizing, no extra code. The software you built is the capture tool.

Review your captures:
```bash
# View all snapshots (Mac)
open snapshot_*.bmp

# Or enlarge for easier viewing
python -c "
import cv2
import sys
for f in sys.argv[1:]:
    img = cv2.imread(f)
    big = cv2.resize(img, (640, 320), interpolation=cv2.INTER_NEAREST)
    cv2.imshow(f, big)
cv2.waitKey(0)
" snapshot_*.bmp
```

---

## Open Questions

1. **Portrait or Landscape?**
   - Face fits better in 32x64 (portrait mode)
   - Current matrix is 64x32 (landscape)
   - Could rotate matrix or crop to square region

2. **Color depth?**
   - RGB565 (65K colors) vs indexed palette (16-256 colors)
   - Fewer colors = more stylized, possibly better aesthetic

3. **Animation frame rate?**
   - LED matrix runs at 5 FPS
   - Enough for expressions, not for lip sync
   - Could increase to 10 FPS for smoother animation

4. **Input method for live avatar?**
   - Keyboard triggers (press 's' for smile)
   - Mouse position controls expression blend
   - Webcam face tracking drives expressions
   - Audio input for reactive expressions

---

## Estimated Effort

| Phase | Time | Output |
|-------|------|--------|
| Proof of concept | 2 hours | Single test image on matrix |
| Capture mode | 4 hours | Modified camera_feed.py |
| Capture session | 1 hour | 50 organized images |
| Simple blender | 4 hours | Real-time expression mixing |
| Polish & iterate | 8+ hours | Usable avatar system |

**Total MVP: ~20 hours**

---

## Why This Could Be Cool

1. **Retro aesthetic**: Pixel art avatars are having a moment
2. **Privacy-preserving**: 2,048 pixels isn't enough for facial recognition
3. **Unique output**: Nobody else has a 64x32 LED portrait of themselves
4. **Tangible**: Physical LED display beats another screen
5. **Extensible**: Could become desk buddy, stream avatar, door greeter

---

*Proposal created for LED Portal project*
