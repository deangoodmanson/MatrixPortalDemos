# Digital Avatar from LED Matrix Headshots

*Last revised: 2026-04-20. Original proposal authored pre-Phase-1. This revision folds in what actually shipped, cuts stale scope, and gives Phase 2 a concrete design.*

## The Idea (unchanged)

Capture multiple headshots at 64×32 resolution using the LED Portal system, then use these to generate an animated digital avatar. The intentionally low resolution creates a pixel-art aesthetic that sidesteps the "uncanny valley" — our brains don't expect photorealism from 2,048 pixels.

| Challenge with HD Avatars | How 64×32 Helps |
|---------------------------|-----------------|
| Uncanny valley from "almost real" faces | Clearly stylized — reads as pixel art |
| Subtle expression errors feel wrong | Limited pixels = exaggerated, readable expressions |
| Lighting inconsistencies are jarring | Reduced color depth hides imperfections |
| High compute requirements | Tiny images = fast processing |

**Aesthetic reference**: Commodore 64 portraits, Game Boy Camera, Celeste-style pixel art.

---

## Model Usage Protocol

This project uses multiple Claude models strategically. **Claude must pause and notify the user before crossing any `MODEL SWITCH POINT` marker below.** Do not silently continue past one — the user wants an explicit handoff moment so they can run `/model` and confirm.

| Model | Use for |
|---|---|
| **Opus 4.7** | Architecture, schema design, ambiguous problems, gnarly debugging, post-surprise re-planning. |
| **Sonnet 4.6** | Bulk implementation once the plan is concrete — CLI scaffolding, pipeline code, unit tests, palette/sprite logic, YAML serialization. |
| **Haiku 4.5** | Mechanical/repetitive passes — bulk renames, boilerplate test scaffolding, grep-and-edit sweeps. |

**Handoff rule**: when Claude hits a `MODEL SWITCH POINT` marker (or encounters a design-level surprise mid-implementation), stop, surface the decision, and wait for the user to switch models before continuing.

---

## Phase 1 Retrospective: What Shipped vs. What Was Proposed

Phase 1 (the capture pipeline) is **complete and in `pro/`**. Details:

- **Trigger**: `v` key (originally proposed `a`) → `AvatarCaptureManager` in `pro/src/ledportal_pro/ui/avatar.py`.
- **Poses**: **18** across 5 angles (front 8, left 3, right 3, up 2, down 2). Proposal called for 25 as the MVP floor, so we're short.
- **Voice prompts**: Added (not in original proposal) via `pro/src/ledportal_pro/ui/tts.py` — each pose is spoken aloud so the subject doesn't have to read a screen while posing.
- **Controls**: SPACE capture / S skip / R repeat prompt / Q quit.
- **Output per session**: `avatar_YYYYMMDD_HHMMSS/` containing `avatar_<angle>_<expression>.bmp`, matching `.bin` RGB565 dumps, and `manifest.json` with structured capture metadata.
- **Tests**: 19 passing (`pro/tests/test_avatar.py`).

### What we learned from shipping Phase 1

1. **Voice prompts are the killer UX feature.** Don't cut them. The subject needs hands-and-eyes free.
2. **18 poses takes ~4-5 minutes**. Adding more will hurt session UX. Favor smarter use of the captures we have over raising the count.
3. **No alignment step exists.** Each capture is independent — subject's head drifts frame-to-frame. Naive blending will look jittery.
4. **No palette step exists.** Each BMP is a 64×32 RGB565 downsample of the raw camera frame, with whatever colors the camera happened to produce.
5. **Manifest is machine-readable.** Phase 2 can consume `manifest.json` directly; we don't need a separate curation UI to start.

### Gaps to close before Phase 2 feels complete

- **Add 7 more poses** to hit 25, specifically the expressions the proposal flagged but we dropped: furrowed brows (front), eyes closed (left/right), speaking poses (A/E/O mouth shapes at left and right). Cheap to add; makes Phase 2 blending meaningfully richer.
- **Capture quality toggle**: capture a burst of 3-5 frames per pose, keep the sharpest (variance-of-Laplacian). Proposal mentioned this; we didn't build it. Uncanny-valley aside, blurry input = bad avatar.
- **Save the raw camera frame** alongside each 64×32 BMP. Landmark detection needs full-resolution input; Phase 2 cannot reach its best output without this.

### Phase 1a Implementation Spec (finalized on Opus, hand to Sonnet)

**File touch list**
- `pro/src/ledportal_pro/ui/avatar.py` — extend `AVATAR_POSES`, extend `CapturedPose`, change `_capture_single_pose` to burst+select and save raw.
- `pro/tests/test_avatar.py` — update pose-count test (18 → 25), add new tests.
- No CLI / config changes needed. Existing `v` key continues to trigger.

**New poses (7 additions → 25 total)**

Append to `AVATAR_POSES` in this order:
```
("front", "furrowed",      "Front facing, furrow your brows like you're concentrating")
("left",  "eyes_closed",   "Stay left, close your eyes")
("left",  "mouth_o",       "Stay left, make an O shape with your mouth")
("right", "eyes_closed",   "Stay right, close your eyes")
("right", "mouth_o",       "Stay right, make an O shape with your mouth")
("up",    "eyebrows_up",   "Chin tilted up, raise your eyebrows")
("down",  "eyebrows_up",   "Chin tilted down, raise your eyebrows")
```

Rationale: fills the brow-down gap (front_furrowed), gives side-profile eye-closed and side-profile mouth sprites (needed for left/right gaze variants in Phase 2), and rounds out up/down brow coverage.

**Burst capture**
- On SPACE, capture a burst of **5 frames** (back-to-back via `camera.capture()`, no sleep between).
- Score each with **variance of Laplacian** (`cv2.Laplacian(gray, cv2.CV_64F).var()`) — higher = sharper.
- Keep the highest-scoring frame as the pose's canonical capture.
- Scores and burst count get written into `manifest.json` (see below).

**Raw frame save**
- Each captured pose now writes three artifacts instead of two:
  - `avatar_<angle>_<expression>.bmp` — 64×32 downsample (existing).
  - `avatar_<angle>_<expression>.bin` — RGB565 bytes (existing).
  - `avatar_<angle>_<expression>_raw.png` — **new**, the full-resolution camera frame (pre-downsample, pre-crop) saved as lossless PNG.
- Rationale: MediaPipe Face Landmarker needs full-resolution input. PNG chosen over NPY/JPG for inspectability + losslessness.

**`CapturedPose` dataclass additions**
```python
@dataclass
class CapturedPose:
    pose_number: int
    angle: str
    expression: str
    filename: str                    # existing, the .bmp
    raw_filename: str                # NEW
    sharpness_score: float           # NEW — winning frame's Laplacian variance
    burst_size: int                  # NEW — always 5 for now, future-proofs it
```

**Manifest schema addition**

Extend each `captured` entry with the new fields. Existing readers should still work since we're only adding keys.

**Test updates** (`pro/tests/test_avatar.py`)
- Update `test_pose_count`: `18` → `25`.
- Update `test_no_duplicate_angle_expression_pairs` — still passes; new entries are unique.
- Add `test_all_angles_have_eyebrows_up` — sanity check on the new up/down additions.
- Add `test_manifest_includes_sharpness_fields` — verify the extended schema round-trips through `_save_manifest`.
- Keep `test_front_has_most_expressions` — front is now 9, others max at 5, still holds.

**Out of scope for Phase 1a** (deliberate)
- No palette quantization.
- No landmark detection.
- No UI change to show sharpness score during capture (just log it).
- No migration of old sessions — older `manifest.json` files without the new fields remain readable.

---

> **MODEL SWITCH POINT → Sonnet.** Spec above is complete. Implementation is mechanical from here: 7 list entries, a dataclass extension, a burst loop with argmax, an extra file write, and test updates. Hand off now.

---

## Revised Approach for Phase 2+

The original proposal framed Phase 2 as "blend neutral ↔ smile with NumPy." That's too naive for this resolution — direct pixel blending of unaligned faces produces ghosting, not expression. **We now have better options that didn't exist (or weren't practical) when the proposal was written.**

### Design pivot: feature decomposition, not whole-frame blending

Rather than crossfading entire 64×32 frames, decompose each captured face into **layers**:

- **Base head** — skin tone region, hairline, silhouette (from front-neutral, palette-quantized).
- **Eyes** — a small sprite (e.g. 12×4 px) extracted by landmark-guided crop, with variants: open, closed, looking-left, looking-right, eyebrow-up.
- **Mouth** — a small sprite (e.g. 14×5 px) with variants: neutral, smile-closed, smile-open, O, EE.
- **Overlay** — optional brow-furrow, glasses, hat.

The avatar at runtime is: `base + eye_sprite[state] + mouth_sprite[state] + overlay`. Expression changes swap sprites; they don't blend frames. **This is how Miis, Animojis, and most modern stylized avatars work**, and it maps cleanly to 64×32: each feature sprite is tiny, hand-reviewable, and can be hand-tweaked without retouching a whole frame.

Why this is a better fit than the proposal's morph-target approach:

| | Whole-frame blend (old plan) | Feature sprites (new plan) |
|---|---|---|
| Handles head drift between captures | ❌ ghosts badly | ✅ sprites are re-aligned per feature |
| Combinatorial expressions (smile + eyes closed) | ❌ needs a capture for every combo | ✅ free — mix any eye with any mouth |
| Human-editable output | ❌ would need to repaint frames | ✅ sprites fit in a pixel-art editor window |
| Animation smoothness | ❌ limited by capture count | ✅ interpolate sprite positions, not pixels |

### The tool we need: `ledportal-avatar`

A standalone CLI in `pro/` (new subcommand or sibling package), built with the same tooling (`uv`, `ruff`, `ty`, `pytest`). Three subcommands:

- **`build <session_dir>`** — consumes a capture session, produces an `avatar_asset.yaml` + sprite sheet PNG.
- **`play <asset_dir>`** — loads an asset and drives the LED matrix with a state machine (idle → blink, talk, react).
- **`preview <asset_dir>`** — scaled-up on-screen preview (no hardware needed), for iteration.

### Pipeline inside `build`

1. **Load manifest**, validate all 18-25 pose files exist.
2. **Upscale for processing**. The BMPs are 64×32 — too small for landmark detection. Also save raw camera frames during capture (new requirement; Phase 1 only kept the downsampled BMP). Land­markers run on the raw frames; results are mapped back to the 64×32 space.
3. **Landmark detection** with **MediaPipe Face Landmarker Task** (478 points + 52 blendshape coefficients). Mature, on-device, no training. Extracts eye/mouth/brow regions directly.
4. **Palette extraction**. K-means or median-cut to **8-16 colors** from the front-neutral pose. Every sprite quantizes to this palette so the whole avatar feels coherent. Fewer colors = more stylized.
5. **Feature sprite extraction**. For each pose, crop the landmark-defined eye/mouth region → downsample → palette-snap → save as indexed sprite.
6. **Sprite de-duplication**. Many captures will produce near-identical sprites (e.g., "front_neutral" and "up_neutral" likely have the same mouth). Hash and dedupe so the sheet stays small.
7. **Emit asset bundle** (contract locked in `schema.py`):
   ```
   avatar_asset/
   ├── avatar.yaml         # single source of truth: palette, anchors, variants, metadata
   ├── base.png            # 64×32 indexed-color PNG, no transparency
   ├── eyes_sheet.png      # horizontal strip of indexed sprites (tRNS for transparency)
   ├── mouth_sheet.png     # horizontal strip of indexed sprites
   └── overlays/           # optional (brow_furrow, glasses, hat)
   ```

   **Schema decisions locked** (`pro/src/ledportal_pro/avatar/schema.py`, `SCHEMA_VERSION = 1`):
   - Palette lives in the YAML as a list of 4-16 `#RRGGBB` hex strings. No separate `palette.txt` (simpler, single-source-of-truth). RGB565 conversion happens at render time, not on disk.
   - Sprite sheets are horizontal strips of equal-width variants. A `variants: [open, closed, ...]` list in the YAML names each column in order; `SpriteSheetSpec.variant_index(name)` resolves the lookup.
   - Each sprite sheet / overlay declares a `transparent_index` (palette index treated as alpha) and an `anchor: [x, y]` top-left on the base canvas.
   - State machine / driver logic is **not** in the YAML. Schema describes what variants exist; drivers in `player.py` decide which to show. Keeps the asset contract decoupled from behavior.
   - Overlays are an ordered list, drawn last over everything else.

### Phase 2 deliverables (concrete, testable)

- `pro/src/ledportal_pro/avatar/builder.py` — the `build` pipeline.
- `pro/src/ledportal_pro/avatar/schema.py` — typed `AvatarAsset` dataclass + YAML schema.
- `pro/src/ledportal_pro/avatar/player.py` — the state machine + LED matrix output.
- Unit tests for palette extraction, sprite cropping, asset serialization (all non-hardware, fast).
- `uv run ledportal-avatar build avatar_20260420_.../` produces a loadable asset and a preview PNG.

> **MODEL SWITCH POINT → Opus** *for schema design*, then **Sonnet** *for implementation*.
> - Opus: lock down `schema.py` (the `AvatarAsset` dataclass, sprite indexing convention, YAML shape). These are contracts everything else depends on.
> - Sonnet: everything else in Phase 2 — builder pipeline, player state machine, preview tool, tests. Pause and prompt for the handoff once the schema is reviewed.
> - Return to Opus if MediaPipe output doesn't match assumptions, palette quantization misbehaves, or alignment math goes sideways.

### Phase 3: live driver

Once Phase 2 produces a playable asset, Phase 3 makes it responsive:

- **Keyboard driver** (trivial): `1`=neutral, `2`=smile, `3`=surprise, etc. Good for streaming/demos.
- **Webcam driver** (cool): MediaPipe runs on the live camera → blendshape coefficients pick which eye/mouth sprite to show. Essentially a 64×32 pixel-art mirror. This was the proposal's "Phase 4 stretch"; with Mediapipe's task API it's now a few days' work, not weeks.
- **Audio driver** (fun): mic input → mouth shape (simple energy + formant heuristic, or a tiny Whisper phoneme model). Good for a "streamer avatar" application.

> **MODEL SWITCH POINT → Opus** *at the start of each driver*, then **Sonnet** *for build-out*. Each driver has a small design moment (state machine shape, blendshape→sprite mapping, audio feature extraction) that benefits from Opus; once that's settled the code itself is straightforward.

### Phase 3 Driver Interface (locked 2026-04-20)

Designed on Opus before Sonnet implementation. The interface prioritises three things: **(1) drivers stay portable across avatars built from different capture sessions, (2) drivers don't need to know avatar-internal variant names, (3) the compositing invariant — eye and mouth variants can come from different source captures — is preserved and controllable.**

#### Abstraction layers

```
Driver (keyboard/webcam/audio)  →  DriverState  →  VariantResolver  →  {feature: variant}  →  AvatarPlayer
     semantic intent                semantic vocab      (owns asset)      (variant names)         (PNG pixels)
```

Only the resolver knows the variant-name convention. Drivers are pure semantic producers; the player is a pure name-keyed renderer.

#### `DriverState` — semantic vocabulary

A tiny dataclass. Fields are `None` when the driver wants to leave that axis unchanged:

```python
@dataclass
class DriverState:
    angle:  str | None = None   # "front" | "left" | "right" | "up" | "down"
    eyes:   str | None = None   # "open" | "closed" | "raised" | "furrowed"
    mouth:  str | None = None   # "neutral" | "smile" | "smile_open" | "o" | "ee" | "closed"
```

The two feature axes (`eyes`, `mouth`) are independent: a driver can set `mouth="smile"` while leaving eyes untouched. This is the whole point of the feature-sprite decomposition — the driver can mix eye state from one semantic with mouth state from another.

#### `Driver` Protocol

```python
@runtime_checkable
class Driver(Protocol):
    def poll(self, dt: float) -> DriverState: ...
    def should_stop(self) -> bool: ...
    def close(self) -> None: ...
```

- `poll(dt)` called once per frame by the loop. `dt` is seconds since last call.
- `should_stop()` checked each tick. True → loop exits cleanly.
- `close()` releases camera/audio/stdin. Always called in the loop's `finally`.

No inheritance required — Protocol with `runtime_checkable`.

#### `VariantResolver` — semantic → variant

Built from an `AvatarAsset`. Encodes the one piece of naming-convention knowledge in the system: the capture's `{angle}_{expression}` pattern and this fixed expression → (eye_sem, mouth_sem) table:

```python
_EXPRESSION_SEMANTICS: dict[str, tuple[str, str]] = {
    "neutral":      ("open",     "neutral"),
    "smile":        ("open",     "smile"),
    "smile_open":   ("open",     "smile_open"),
    "eyebrows_up":  ("raised",   "neutral"),
    "eyes_closed":  ("closed",   "neutral"),
    "mouth_o":      ("open",     "o"),
    "mouth_ee":     ("open",     "ee"),
    "mouth_closed": ("open",     "closed"),
    "furrowed":     ("furrowed", "neutral"),
}
```

At construction, the resolver indexes each variant by `(angle, eye_sem)` and `(angle, mouth_sem)`. `resolve()` merges the incoming DriverState with the last-resolved semantic (so partial updates work), then looks up each feature independently with a fallback chain:

1. Exact `(angle, sem)` match.
2. `("front", sem)` — front-facing fallback when the angle wasn't captured.
3. Any variant with that semantic, regardless of angle.
4. First variant in the list (last resort).

Returns only the features whose variant changed, so `player.set_state` isn't called redundantly.

#### `AvatarLoop` — the runner

```python
class AvatarLoop:
    def __init__(
        self,
        player: AvatarPlayer,
        driver: Driver,
        resolver: VariantResolver,
        target_fps: float = 15.0,
    ): ...

    def run(self) -> None:
        """Blocking. Polls driver, resolves, renders, pushes to transport until
        driver.should_stop() returns True or KeyboardInterrupt. Always calls
        driver.close() in finally."""
```

Frame budget: `1.0 / target_fps`. If the render+send took longer, skip the sleep. The matrix is happy at 10-15 fps; sprite composites are cheap, so target 15.

#### `BlinkFilter` — driver middleware

Auto-blink is an avatar quality-of-life feature, not a driver concern. Solve with a wrapper:

```python
class BlinkFilter:
    """Wraps any Driver; injects 'eyes=closed' briefly at randomised intervals
    whenever the inner driver's eyes would be 'open'."""

    def __init__(
        self,
        inner: Driver,
        interval_range: tuple[float, float] = (3.0, 7.0),
        blink_duration: float = 0.12,
    ): ...
```

Conforms to `Driver` itself. Composable: `BlinkFilter(KeyboardDriver())`, `BlinkFilter(WebcamDriver())`, etc.

#### Concrete drivers in Phase 3

| Driver | Input | Mapping strategy |
|---|---|---|
| `KeyboardDriver` | Non-blocking stdin keypresses | `1-4` → eye semantics, `5-9` → mouth semantics, `WASDE` → angle. `Q`/`Esc` → stop. |
| `WebcamDriver` | MediaPipe Face Landmarker with `output_face_blendshapes=True` on live OpenCV frames | Blendshape coefficients threshold-mapped to semantics. Face transformation matrix (requires `output_facial_transformation_matrixes=True`) → yaw/pitch → angle. |
| `AudioDriver` *(stretch)* | PyAudio mic stream | RMS energy + zero-crossing heuristic → mouth semantic only; angle/eyes unchanged. |

**Webcam blendshape thresholds** (starting values — expect iteration during real-face testing):

| Blendshape(s) | Semantic |
|---|---|
| `eyeBlinkLeft`/`eyeBlinkRight` avg > 0.55 | `eyes="closed"` |
| `browInnerUp` + `browOuterUp*` avg > 0.30 | `eyes="raised"` |
| `browDownLeft/Right` avg > 0.30 | `eyes="furrowed"` |
| (else) | `eyes="open"` |
| `jawOpen` > 0.40 | `mouth="o"` |
| `mouthSmile*` avg > 0.35 and `jawOpen` > 0.25 | `mouth="smile_open"` |
| `mouthSmile*` avg > 0.35 | `mouth="smile"` |
| `mouthFunnel` > 0.30 | `mouth="ee"` |
| (else) | `mouth="neutral"` |

**Angle from transformation matrix** (Euler extraction):

| Range | Angle |
|---|---|
| yaw > +20° | `"right"` |
| yaw < −20° | `"left"` |
| pitch < −15° | `"up"` |
| pitch > +15° | `"down"` |
| (else) | `"front"` |

#### File layout

```
pro/src/ledportal_pro/avatar/
├── drivers.py          # DriverState, Driver Protocol
├── resolver.py         # VariantResolver + _EXPRESSION_SEMANTICS
├── loop.py             # AvatarLoop + BlinkFilter
└── drivers_impl/
    ├── __init__.py
    ├── keyboard.py     # KeyboardDriver
    ├── webcam.py       # WebcamDriver (requires mediapipe + model)
    └── audio.py        # AudioDriver (stretch)
```

Wire `ledportal-avatar play --driver keyboard|webcam|audio [--no-blink]` in `cli.py`.

#### Tests

- `test_resolver.py` — semantic→variant with all four fallback tiers; partial DriverState merging; angle-only updates re-lookup current semantics at new angle.
- `test_loop.py` — synthetic driver (yields a prescripted state sequence) + mock player; verify frame timing, stop signal, close-on-exception.
- `test_blink_filter.py` — with a steady-state inner driver, verify blinks fire within interval range and stop firing when inner is already `eyes="closed"`.
- `test_keyboard_driver.py` — inject fake stdin bytes, assert emitted DriverStates.
- `test_webcam_driver.py` — **mock the mediapipe result**, verify blendshape thresholds map correctly. No live camera or model file in CI.

> **MODEL SWITCH POINT → Sonnet.** Interface is locked. Phase 3a (KeyboardDriver + Loop + Resolver + BlinkFilter + tests) is entirely mechanical from here — 150-250 LOC total. Phase 3b (WebcamDriver) is also mechanical once the blendshape table above is fixed. Hand off now.

### Phase 4: ideas parked for later

- **Blink/idle animation loop** — automatic micro-animations when no driver input.
- **Multi-subject library** — one `~/.ledportal/avatars/` per person, `v`+person selector.
- **Macropad integration** — already have `macropad/`; map pad keys to expression triggers during streams.
- **AI-generated intermediate sprites**. Claude API (vision + image output) or a local diffusion model could fill in missing expressions from the captured set. Interesting but not on the critical path.

---

## Decisions (old open questions, now resolved)

| Question (from original proposal) | Decision |
|---|---|
| Portrait or landscape? | **Landscape (64×32)**. Proposal agonized over this; in practice, center-cropping to a ~26-wide face region inside the 64-wide frame works fine and leaves room for animated side elements (name tag, mood ring). |
| Color depth? | **8-16 color indexed palette** per avatar, rendered back to RGB565 at display time. Fewer colors is the whole aesthetic. |
| Animation frame rate? | **Target 15 FPS** for the avatar loop. Sprite swaps don't need interpolation, so this is cheap. |
| Input method? | **Keyboard first, webcam-tracking second, audio third.** Webcam is the demo that sells it. |

## New open questions

1. **Where does the asset live?** Inside the session dir, or a sibling `~/.ledportal/avatars/`? Leaning sibling — assets are reusable across sessions.
2. **Should `play` be a new subcommand of `ledportal`, or a new binary?** Leaning subcommand, so it shares the transport and matrix config.
3. **Does Phase 1 need a re-capture pass to hit 25 poses + raw-frame dump?** Likely yes, before Phase 2 can produce its best output. Can ship Phase 2 against existing 18-pose sessions with degraded quality and revise.

---

## Libraries (pruned to what we'll actually use)

| Library | Role |
|---|---|
| **Pillow** | Palette quantization, PNG sprite sheets (already a project dep via `utils/`). |
| **NumPy** | Array math for cropping/indexing. |
| **OpenCV** | Already in use for capture. Reused for sharpness scoring during burst capture. |
| **MediaPipe Tasks (Python)** | Face Landmarker + blendshapes. Replaces dlib/StyleGAN/PIFuHD from the old proposal — it subsumes all of them for our needs. |
| **PyYAML** | Asset manifest serialization. |

**Dropped from the original proposal**: Pygame, Arcade, Pyxel (we don't need a game engine; we just blit to the matrix), StyleGAN3 (overkill and dated), PIFuHD (3D reconstruction irrelevant at 64×32), Ebsynth (not Python, not on path), Stable Diffusion + ControlNet (nice future experiment, not critical path).

---

## Revised effort estimate

Recalibrated against the "it's 2026 and we have capable coding assistance" baseline:

| Phase | Effort | Output |
|---|---|---|
| 1a. Re-capture (25 poses + raw frames + burst sharpness) | 2-3 hrs | Upgraded session data |
| 2a. Asset schema + builder pipeline | 1 day | `ledportal-avatar build` produces asset |
| 2b. Player + state machine | 0.5 day | `ledportal-avatar play` on matrix |
| 2c. Preview tool + tests | 0.5 day | Iteration loop without hardware |
| 3a. Keyboard-driven expressions | 2 hrs | Live expression control |
| 3b. MediaPipe live driver | 1-2 days | Pixel-art mirror demo |
| 3c. Audio driver | 1 day (stretch) | Talking avatar for streams |

**Phase 2 MVP: ~2-3 days.** Phase 3 demo-ready: **~1 week total.**

---

## Why this is still worth building

1. **Retro aesthetic** holds up — pixel art avatars keep trending.
2. **Privacy-preserving** — 2,048 pixels is well below any facial-recognition threshold.
3. **Tangible** — it's a physical LED display; stands alone on a desk or at a booth.
4. **Educational value** — touches palette quantization, landmark detection, sprite compositing, state machines. Good material for the `hs/` port later.
5. **Extensible** — desk buddy, stream avatar, door greeter, macropad-driven performer.
