namespace LedPortal.Config;

// ── Enums ──────────────────────────────────────────────────────────────────

public enum Orientation { Landscape, Portrait }
public enum ProcessingMode { Center, Stretch, Fit }
public enum InterpolationMode { Nearest, Linear, Area, Cubic }

// ── Config records ─────────────────────────────────────────────────────────
// Records are immutable value types. Runtime changes (key presses) produce new
// records via C# `with` expressions rather than mutating shared state.
// Example: config = config with { TargetFps = 15 };

public record MatrixConfig(int Width = 64, int Height = 32)
{
    // Computed property — equivalent to Python @property
    public int FrameSizeBytes => Width * Height * 2;
}

public record CameraConfig(
    int Width = 0,   // 0 = use native resolution
    int Height = 0,
    int Index = 0);

public record TransportConfig(
    int BaudRate = 4_000_000,
    double Timeout = 0.1,
    double WriteTimeout = 0.5,
    string FrameHeader = "IMG1");

public record ProcessingConfig(
    InterpolationMode Interpolation = InterpolationMode.Linear,
    bool EnableGammaCorrection = false,
    double Gamma = 2.2,
    int MaxBrightness = 255,
    Orientation Orientation = Orientation.Landscape,
    ProcessingMode ProcessingMode = ProcessingMode.Center);

public record UiConfig(
    double CountdownDuration = 0.5,
    double SnapshotPauseDuration = 3.0,
    bool EnableFrameLimiting = false,
    bool DebugMode = false,
    bool ShowPreview = false);

public record AppConfig(
    MatrixConfig Matrix,
    CameraConfig Camera,
    TransportConfig Transport,
    ProcessingConfig Processing,
    UiConfig Ui,
    int TargetFps = 30,
    bool DebugSaveFrames = false)
{
    // Frame time in milliseconds for PeriodicTimer
    public double FrameTimeMs => 1000.0 / TargetFps;

    // Convenience factory for defaults — mirrors Python's field(default_factory=...)
    public static AppConfig CreateDefault() => new(
        new MatrixConfig(),
        new CameraConfig(),
        new TransportConfig(),
        new ProcessingConfig(),
        new UiConfig());
}
