# LED Portal — C# Port

A C# .NET 10 port of `pro/` — the professional LED matrix camera feed application. This version is a learning exercise designed to explore modern C# idioms by porting familiar Python code.

## Prerequisites

- .NET 10 SDK (`dotnet --version` should show `10.x`)
- A USB camera (built-in or external)
- *Optional*: Adafruit Matrix Portal M4/S3 with 64×32 RGB LED matrix

Install .NET 10: https://dotnet.microsoft.com/download/dotnet/10

## Quick Start

```bash
cd csharp
dotnet run --project src/LedPortal -- --config src/LedPortal/Config/configs/mac.yaml
```

Run tests:

```bash
dotnet test tests/LedPortal.Tests
```

## Project Structure

```
csharp/
├── LedPortal.sln
├── src/LedPortal/
│   ├── LedPortal.csproj
│   ├── Program.cs                    # Entry point, main loop
│   ├── Config/
│   │   ├── AppConfig.cs              # Immutable record config tree
│   │   ├── ConfigLoader.cs           # YamlDotNet deserialization
│   │   └── configs/
│   │       ├── default.yaml
│   │       └── mac.yaml
│   ├── Exceptions/
│   │   └── LedPortalExceptions.cs    # Full exception hierarchy
│   ├── Capture/
│   │   ├── ICamera.cs
│   │   ├── OpenCvCamera.cs
│   │   └── CameraFactory.cs
│   ├── Transport/
│   │   ├── ITransport.cs
│   │   ├── SerialTransport.cs
│   │   └── TransportFactory.cs
│   ├── Processing/
│   │   ├── ColorProcessor.cs         # RGB565, grayscale, mirror, brightness, gamma
│   │   ├── FrameResizer.cs           # Center crop, letterbox, stretch, portrait
│   │   ├── ZoomCropper.cs
│   │   └── TestPatterns.cs
│   └── UI/
│       ├── InputCommand.cs           # Enum + non-blocking KeyboardHandler
│       ├── PreviewWindow.cs          # 3-pane OpenCV preview + LED render modes
│       ├── SnapshotManager.cs        # BMP saving with orientation correction
│       ├── DemoMode.cs               # Auto/manual feature showcase state machine
│       └── ConsoleHelp.cs
└── tests/LedPortal.Tests/
    ├── LedPortal.Tests.csproj
    ├── Fixtures/FrameHelpers.cs
    ├── Config/ConfigTests.cs
    └── Processing/
        ├── ColorProcessorTests.cs
        ├── FrameResizerTests.cs
        ├── ZoomCropperTests.cs
        └── TestPatternsTests.cs
```

## NuGet Dependencies

| Package | Purpose |
|---------|---------|
| `OpenCvSharp4` | Camera capture, image processing, preview window |
| `OpenCvSharp4.runtime.osx-arm64` | Native OpenCV binaries (Apple Silicon) |
| `YamlDotNet` | YAML config loading |
| `System.CommandLine` | CLI argument parsing |
| `xunit` (tests) | Unit test framework |

## Python → C# Design Mapping

This port deliberately uses C# idioms rather than translating Python line-by-line. The table below highlights the most interesting differences.

| Python pattern | C# equivalent | Why it's interesting |
|----------------|---------------|----------------------|
| `@dataclass` (mutable) | `record` (immutable) + `with` expressions | State changes are explicit; no aliasing bugs |
| Abstract base class `CameraBase` | `interface ICamera : IDisposable` | Cleaner contracts; no ABC machinery needed |
| `__enter__` / `__exit__` | `IDisposable` + `using` | Deterministic disposal regardless of GC timing |
| `numpy` byte arrays | `Span<byte>`, `Memory<byte>` | Zero-copy stack/heap buffers; `ReadOnlySpan<byte>` prevents mutation |
| `struct.pack("<H", v)` | `BinaryPrimitives.WriteUInt16LittleEndian(span, v)` | Explicit endianness, documents intent |
| `time.sleep()` frame limiter | `PeriodicTimer` + `await` | Self-correcting, drift-resistant async timing (.NET 6+) |
| `KeyboardInterrupt` | `CancellationToken` | Cooperative cancellation — composable and testable |
| `select.select()` on stdin | `Console.KeyAvailable` | No `termios`/platform handling needed |
| `match`/`case` (Python 3.10+) | `switch` expression | Compiler warns on unhandled enum cases |
| `Optional[T]` / `T \| None` | `T?` nullable reference types | Null safety enforced at compile time |
| `dict` for config overrides | `record with { }` | Immutable; each mutation produces a new object |

## Key Algorithms

### RGB565 Encoding (`ColorProcessor.cs`)

Converts a 64×32 BGR frame (from OpenCV) to 4,096 bytes of RGB565 for the LED matrix:

```csharp
// BGR → RGB, then pack into 16-bit little-endian
ushort r = (ushort)((pixel.R >> 3) & 0x1F);  // 5 bits
ushort g = (ushort)((pixel.G >> 2) & 0x3F);  // 6 bits
ushort b = (ushort)((pixel.B >> 3) & 0x1F);  // 5 bits
ushort rgb565 = (ushort)((r << 11) | (g << 5) | b);
BinaryPrimitives.WriteUInt16LittleEndian(outSpan[offset..], rgb565);
```

`BinaryPrimitives` replaces numpy's `dtype("<u2").tobytes()` and is correct on any-endian hardware.

### Frame Pipeline

```
Camera.Capture()         → BGR Mat (full resolution)
ZoomCropper              → center-cropped Mat (if zoom < 1.0)
FrameResizer             → BGR Mat 64×32 (center crop / letterbox / stretch)
ColorProcessor           → mirror, grayscale, brightness limit, gamma
ColorProcessor           → byte[] RGB565 (4,096 bytes)
SerialTransport          → "IMG1" header + RGB565 → Matrix Portal → LED matrix
PreviewWindow            → 3-pane OpenCV window (raw | matrix | LED render)
```

### Serial Protocol (`SerialTransport.cs`)

- Baud: 4,000,000
- Frame: 4-byte ASCII header `"IMG1"` + 4,096 bytes RGB565
- `DTREnable = false`, `RTSEnable = false` (prevents CircuitPython reset on connect)
- 2 s boot wait after open; 10 ms `Thread.Sleep` after each frame
- `SerialPort.BaseStream.Write(ReadOnlySpan<byte>)` for zero-copy writes (.NET 9)

### LED Preview Render Modes (`PreviewWindow.cs`)

The preview window upscales the 64×32 frame 10× to 640×320 using one of four algorithms:

| Mode | Description |
|------|-------------|
| `Squares` | Nearest-neighbor pixel blocks |
| `Circles` | Hard-edged circles; vectorized mask (≤100%) or painter's algorithm (>100%) |
| `GaussianRaw` | Soft Gaussian blur (sigma ≈ 18% of cell size) |
| `GaussianDiffused` | Gaussian with diffuser simulation (sigma ≈ 27%) |

Inverse sRGB gamma LUT (exponent 1/2.2) is applied to match perceived LED brightness.

### Demo Mode State Machine (`DemoMode.cs`)

```
Off ──x──> Auto ──x──> Paused ──x──> Off
            │                          ^
            └────────X (manual)──> Manual ─┘
```

Auto mode cycles through: orientation → processing modes → B&W → mirror → zoom levels → render algorithms → circle sizes. Each step has a configurable duration and an on-screen label.

## Configuration

YAML files in `src/LedPortal/Config/configs/` mirror the Python `pro/config/` files:

```yaml
# mac.yaml
target_fps: 30
ui:
  show_preview: true
  enable_frame_limiting: false
```

Config is loaded into an immutable `AppConfig` record. Runtime changes (key presses) produce new records via `with` expressions:

```csharp
config = config with {
    Processing = config.Processing with { Orientation = Orientation.Portrait }
};
```

## Keyboard Controls

| Key | Action |
|-----|--------|
| `l` / `p` | Landscape / Portrait orientation |
| `c` / `s` / `f` | Center crop / Stretch / Fit (letterbox) |
| `b` | Toggle black & white |
| `m` | Toggle mirror |
| `z` | Cycle zoom (100% → 75% → 50% → 25% → 100%) |
| `o` | Cycle render algorithm |
| `+` / `-` | LED circle size |
| `SPACE` | Save snapshot (BMP) |
| `t` | Toggle serial transmission |
| `x` / `X` | Demo auto / Demo manual |
| `.` / `,` | Demo next / prev step |
| `d` | Toggle debug mode |
| `w` | Toggle preview window |
| `r` | Reset all settings |
| `h` | Help |
| `q` | Quit |

## Testing

Tests use xUnit and mirror the Python test suite structure.

```bash
dotnet test tests/LedPortal.Tests --logger "console;verbosity=normal"
```

Key test files and their Python counterparts:

| C# test file | Python equivalent |
|---|---|
| `Config/ConfigTests.cs` | `tests/test_config.py` |
| `Processing/ColorProcessorTests.cs` | `tests/test_color.py` |
| `Processing/FrameResizerTests.cs` | `tests/test_resize.py` |
| `Processing/ZoomCropperTests.cs` | `tests/test_zoom.py` |
| `Processing/TestPatternsTests.cs` | `tests/test_patterns.py` |

xUnit `[Theory]` + `[InlineData]` replaces pytest's `@pytest.mark.parametrize`. `[MemberData]` with LINQ combinatorics handles the orientation × processing mode cartesian product in `FrameResizerTests`.

## What's Not Ported

| Feature | Reason |
|---------|--------|
| Avatar capture (17-pose guided session) | TTS + pose management is impractical in a C# console app |
| Text-to-speech | No good cross-platform equivalent; `say`/`espeak` could be shelled out but adds no C# learning value |
| PDF export (`ledportal-utils`) | Local Python package; BMP snapshot is sufficient |
| `picamera2` / Pi Camera | C# on Raspberry Pi is unusual; USB camera via OpenCV covers the use case |

## Relation to Other Versions

| Version | Language | Purpose |
|---------|----------|---------|
| `pro/` | Python 3.14 | Production-ready, modular, fully tested |
| `hs/` | Python 3.14 | Educational single-file with extensive comments |
| `csharp/` | C# .NET 9 | C# learning exercise, mirrors `pro/` architecture |
| `matrix-portal/` | CircuitPython 10 | Firmware running on the LED matrix controller |
