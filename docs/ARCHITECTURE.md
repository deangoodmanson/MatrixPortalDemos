# Architecture

A map of the three applications in this repository and how they fit together.
Written to give a human — or an AI coding agent — enough of the shape to make a
change in the right place without reading every file first.

The diagrams below use [Mermaid](https://mermaid.js.org/), which GitHub renders
natively. Symbol names (`create_camera`, `receive_frame`, etc.) match the actual
code so you can jump straight from a box to a function.

> **Resolution note:** the matrix is **64×32** (landscape). Portrait mode is the
> same panel rotated 90° (a 32×64 logical plane). Frames are **RGB565**
> (2 bytes/pixel = 4096 bytes/frame) sent over **USB CDC serial at 4 Mbaud**.

---

## 1. System overview — three apps, one pipeline

Two of the apps are **host-side** Python (run on a Mac/PC/Pi); one is
**device-side** CircuitPython firmware (runs on the Matrix Portal M4). The host
captures and processes camera frames; the firmware receives and displays them.

```mermaid
flowchart LR
    subgraph HOST["Host (Mac / PC / Raspberry Pi) — Python 3.14"]
        PRO["pro/<br/>ledportal_pro<br/>(modular, typed, tested)"]
        HS["hs/<br/>camera_feed.py<br/>(single-file, educational)"]
    end

    subgraph DEVICE["Matrix Portal M4 — CircuitPython 10"]
        FW["matrix-portal/<br/>code.py + image_display.py + silly_bird.py"]
    end

    CAM(["USB / Pi Camera"])
    PANEL(["64×32 RGB LED matrix<br/>(HUB75)"])

    CAM --> PRO
    CAM --> HS
    PRO -->|"RGB565 frames<br/>USB CDC serial @ 4 Mbaud"| FW
    HS  -->|"RGB565 frames<br/>USB CDC serial @ 4 Mbaud"| FW
    FW --> PANEL
```

`pro/` and `hs/` are **interchangeable host clients** — they speak the same wire
protocol to the same firmware. `pro` is the production/maintainer build; `hs` is
the teaching build (see [`why-learn-to-code.md`](why-learn-to-code.md)). The
firmware doesn't know or care which one is connected.

---

## 2. The wire protocol (host ↔ device)

The contract between every host app and the firmware. Keep both sides in sync
when changing it.

```mermaid
sequenceDiagram
    participant H as Host (transport)
    participant D as Device (image_display.receive_frame)
    participant M as LED matrix

    Note over H,D: USB CDC data port (boot.py: usb_cdc.enable(data=True))
    loop every frame
        H->>D: header b"IMG1" + 4096 RGB565 bytes
        D->>D: rfind("IMG1") → read newest full frame
        D->>M: bitmaptools.arrayblit (C-level copy)
    end
```

- **Header:** `b"IMG1"` (`frame_header` in `pro`'s `TransportConfig`; `FRAME_HEADER`
  in `image_display.py`).
- **Payload:** `width × height × 2` = 4096 bytes, RGB565.
- **"Newest wins":** the device uses `rfind` on the header to skip stale buffered
  frames, so it always displays the latest — this is what keeps latency low.
- **Speed:** `bitmaptools.arrayblit` replaced a Python pixel loop; combined with
  4 Mbaud it's what took the firmware from ~5 FPS to ~24 FPS.

---

## 3. `pro/` — modular host application

Entry point `main.py` wires four subsystems together behind abstract base
classes, choosing concrete implementations via factories. This is the structure
to respect when adding features: put new code in the subsystem it belongs to.

```mermaid
graph TD
    MAIN["main.py<br/>capture→process→transmit loop"]
    CFG["config.py<br/>AppConfig from YAML + CLI"]
    MAIN -.reads.-> CFG

    subgraph CAPTURE["capture/ — camera input"]
        CFAC["create_camera()"] --> CBASE["CameraBase (ABC)"]
        CBASE --> OCV["OpenCVCamera"]
        CBASE --> PICAM["PiCamera"]
    end

    subgraph PROCESS["processing/ — frame pipeline (NumPy)"]
        ZOOM["apply_zoom_crop"] --> RESIZE["resize_frame<br/>center/stretch/fit"]
        RESIZE --> FX["apply_mirror / apply_grayscale /<br/>apply_brightness_limit"]
        FX --> RGB["convert_to_rgb565"]
    end

    subgraph TRANSPORT["transport/ — device output"]
        TFAC["create_transport()"] --> TBASE["TransportBase (ABC)"]
        TBASE --> SER["SerialTransport.send_frame"]
    end

    subgraph UI["ui/ — interaction"]
        INPUT["input.py (keyboard)"]
        OVERLAY["overlay.py (preview render)"]
        SNAP["snapshot.py (BMP/PDF/print)"]
        AV["avatar.py"]
        DEMO["demo.py"]
        TTS["tts.py"]
    end

    MAIN --> CAPTURE
    MAIN --> PROCESS
    MAIN --> TRANSPORT
    MAIN --> UI
    CAPTURE -->|"BGR frame"| PROCESS
    PROCESS -->|"RGB565 bytes"| TRANSPORT
```

**Per-frame loop** (in `main.py`): `camera.capture()` → `apply_zoom_crop` →
`resize_frame` → optional `apply_mirror` / `apply_grayscale` → overlay →
`convert_to_rgb565` → `transport.send_frame`; with an optional `show_preview`
window branch off the processed frame.

**Where to make a change:**
| Task | Location |
|------|----------|
| New camera backend | `capture/` — subclass `CameraBase`, register in `factory.py` |
| New image effect / processing mode | `processing/` — add a function, call it in `main.py`'s loop |
| New output target | `transport/` — subclass `TransportBase` |
| New keyboard command | `ui/input.py` (`InputCommand` enum + key map) + handler in `main.py` |
| New config option | `config.py` (`UIConfig`/etc.) + the relevant YAML in `pro/config/` |

---

## 4. `hs/` — single-file educational application

Same pipeline as `pro`, deliberately collapsed into one linear, heavily-commented
file (`hs/src/camera_feed.py`) with settings in `config.py`. No classes,
factories, or abstractions — the data flow reads top-to-bottom so a student can
follow it. `pro`'s subsystems map to `hs` functions:

```mermaid
graph LR
    SETUP["setup_camera()<br/>(auto: PiCamera → USB)"] --> CAP["capture_frame()"]
    CAP --> RES["resize_frame()<br/>orient + proc mode"]
    RES --> MIR["apply_mirror() /<br/>apply_black_and_white()"]
    MIR --> CONV["convert_to_rgb565()"]
    CONV --> SEND["send over pyserial"]
    SETUP -.->|reads| CONFIG["config.py constants"]
```

The equivalence is intentional: a student who understands `hs/camera_feed.py`
can open `pro/` and recognize the same stages, now separated into modules. That
progression is the teaching arc.

---

## 5. `matrix-portal/` — device firmware

`code.py` is the firmware entry point. It reads `MODE` from `settings.toml` and
dispatches to one or both apps. In the default `both` mode it shows a **hub**
screen and switches between the camera mirror and the Silly Bird game.

```mermaid
graph TD
    BOOT["boot.py<br/>usb_cdc.enable(console+data)"] --> CODE["code.py<br/>read MODE from settings.toml"]
    CODE -->|MODE=image_display| IDLOOP["image_display loop only"]
    CODE -->|MODE=silly_bird| SBLOOP["silly_bird.run() only"]
    CODE -->|MODE=both default| HUB["hub screen<br/>MIRROR / UP:PHOTOS / DN:BIRD"]

    HUB -->|USB frames arrive| MIRROR["image_display.receive_frame<br/>+ display_frame (arrayblit)"]
    HUB -->|UP| PHOTO["image_display.run_photo_mode<br/>built-in BMPs"]
    HUB -->|DOWN / EXT| GAME["silly_bird.run<br/>(state machine)"]
```

- **`image_display.py`** — receives camera frames (`receive_frame`), blits them
  (`display_frame`), and serves the photo slideshow.
- **`silly_bird.py`** — the on-device game; its full screen-flow state machine is
  documented in [`../matrix-portal/NAVIGATION.md`](../matrix-portal/NAVIGATION.md).
- **`settings.toml`** — `MODE` and `BRIGHTNESS` (note: values must be quoted
  strings; CircuitPython 10's TOML parser rejects bare floats).

For deployment, libraries, and the A0 hardware button, see
[`../matrix-portal/README.md`](../matrix-portal/README.md).

---

## Cross-reference

| Concern | Document |
|---------|----------|
| Firmware screen-flow state machine | [`matrix-portal/NAVIGATION.md`](../matrix-portal/NAVIGATION.md) |
| Firmware deploy / hardware | [`matrix-portal/README.md`](../matrix-portal/README.md) |
| `pro` usage, CLI, controls | [`pro/README.md`](../pro/README.md) |
| `hs` setup and learning path | [`hs/README.md`](../hs/README.md) |
| Snapshot / photo-booth printing | [`pro/PRINTING.md`](../pro/PRINTING.md) † |
| Why two editions + agentic build | [`how-this-was-built.md`](how-this-was-built.md) † |

> † These docs land via other open PRs (photo-booth printing, teacher
> onboarding). The links resolve once those branches merge to main.
