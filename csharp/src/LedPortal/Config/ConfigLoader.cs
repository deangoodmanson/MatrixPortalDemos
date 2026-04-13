using LedPortal.Exceptions;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;

namespace LedPortal.Config;

// ── Mutable DTOs for YamlDotNet ────────────────────────────────────────────
// YamlDotNet requires mutable POCOs with setters.
// We map them to immutable records after deserialization.
// This is the standard .NET pattern: mutable DTO → immutable domain model.

internal class MatrixDto
{
    public int Width { get; set; } = 64;
    public int Height { get; set; } = 32;
}

internal class CameraDto
{
    public int Width { get; set; } = 0;
    public int Height { get; set; } = 0;
    public int Index { get; set; } = 0;
    public bool PreferPicamera { get; set; } = true;
}

internal class TransportDto
{
    public int BaudRate { get; set; } = 4_000_000;
    public double Timeout { get; set; } = 0.1;
    public double WriteTimeout { get; set; } = 0.5;
    public string FrameHeader { get; set; } = "IMG1";
}

internal class ProcessingDto
{
    public string Interpolation { get; set; } = "linear";
    public bool EnableGammaCorrection { get; set; } = false;
    public double Gamma { get; set; } = 2.2;
    public int MaxBrightness { get; set; } = 255;
    public string Orientation { get; set; } = "landscape";
    public string ProcessingMode { get; set; } = "center";
}

internal class UiDto
{
    public double CountdownDuration { get; set; } = 0.5;
    public double SnapshotPauseDuration { get; set; } = 3.0;
    public bool EnableFrameLimiting { get; set; } = false;
    public bool DebugMode { get; set; } = false;
    public bool SingleKeypress { get; set; } = true;
    public bool ShowPreview { get; set; } = false;
}

internal class AppConfigDto
{
    public MatrixDto Matrix { get; set; } = new();
    public CameraDto Camera { get; set; } = new();
    public TransportDto Transport { get; set; } = new();
    public ProcessingDto Processing { get; set; } = new();
    public UiDto Ui { get; set; } = new();
    public int TargetFps { get; set; } = 30;
    public bool DebugSaveFrames { get; set; } = false;
}

// ── ConfigLoader ───────────────────────────────────────────────────────────

public static class ConfigLoader
{
    private static readonly IDeserializer _deserializer = new DeserializerBuilder()
        .WithNamingConvention(UnderscoredNamingConvention.Instance)
        .IgnoreUnmatchedProperties()
        .Build();

    private static readonly ISerializer _serializer = new SerializerBuilder()
        .WithNamingConvention(UnderscoredNamingConvention.Instance)
        .Build();

    /// <summary>Load config from a YAML file. Null returns defaults.</summary>
    public static AppConfig Load(string? path = null)
    {
        if (path is null)
            return AppConfig.CreateDefault();

        if (!File.Exists(path))
            throw new ConfigNotFoundException(path);

        try
        {
            var yaml = File.ReadAllText(path);
            var dto = _deserializer.Deserialize<AppConfigDto>(yaml) ?? new AppConfigDto();
            return MapDto(dto);
        }
        catch (Exception ex) when (ex is not ConfigException)
        {
            throw new ConfigValidationException($"Invalid YAML in config file: {ex.Message}", ex);
        }
    }

    /// <summary>Save an AppConfig back to YAML.</summary>
    public static void Save(AppConfig config, string path)
    {
        var dto = new AppConfigDto
        {
            Matrix = new MatrixDto { Width = config.Matrix.Width, Height = config.Matrix.Height },
            Camera = new CameraDto
            {
                Width = config.Camera.Width,
                Height = config.Camera.Height,
                Index = config.Camera.Index,
            },
            Transport = new TransportDto
            {
                BaudRate = config.Transport.BaudRate,
                Timeout = config.Transport.Timeout,
                WriteTimeout = config.Transport.WriteTimeout,
                FrameHeader = config.Transport.FrameHeader,
            },
            Processing = new ProcessingDto
            {
                Interpolation = config.Processing.Interpolation.ToString().ToLower(),
                EnableGammaCorrection = config.Processing.EnableGammaCorrection,
                Gamma = config.Processing.Gamma,
                MaxBrightness = config.Processing.MaxBrightness,
                Orientation = config.Processing.Orientation.ToString().ToLower(),
                ProcessingMode = config.Processing.ProcessingMode.ToString().ToLower(),
            },
            Ui = new UiDto
            {
                CountdownDuration = config.Ui.CountdownDuration,
                SnapshotPauseDuration = config.Ui.SnapshotPauseDuration,
                EnableFrameLimiting = config.Ui.EnableFrameLimiting,
                DebugMode = config.Ui.DebugMode,
                ShowPreview = config.Ui.ShowPreview,
            },
            TargetFps = config.TargetFps,
            DebugSaveFrames = config.DebugSaveFrames,
        };

        Directory.CreateDirectory(Path.GetDirectoryName(path) ?? ".");
        File.WriteAllText(path, _serializer.Serialize(dto));
    }

    private static AppConfig MapDto(AppConfigDto dto) => new(
        Matrix: new MatrixConfig(dto.Matrix.Width, dto.Matrix.Height),
        Camera: new CameraConfig(dto.Camera.Width, dto.Camera.Height, dto.Camera.Index),
        Transport: new TransportConfig(
            dto.Transport.BaudRate,
            dto.Transport.Timeout,
            dto.Transport.WriteTimeout,
            dto.Transport.FrameHeader),
        Processing: new ProcessingConfig(
            Interpolation: ParseInterpolation(dto.Processing.Interpolation),
            EnableGammaCorrection: dto.Processing.EnableGammaCorrection,
            Gamma: dto.Processing.Gamma,
            MaxBrightness: dto.Processing.MaxBrightness,
            Orientation: ParseOrientation(dto.Processing.Orientation),
            ProcessingMode: ParseProcessingMode(dto.Processing.ProcessingMode)),
        Ui: new UiConfig(
            dto.Ui.CountdownDuration,
            dto.Ui.SnapshotPauseDuration,
            dto.Ui.EnableFrameLimiting,
            dto.Ui.DebugMode,
            dto.Ui.ShowPreview),
        TargetFps: dto.TargetFps,
        DebugSaveFrames: dto.DebugSaveFrames);

    private static InterpolationMode ParseInterpolation(string s) => s.ToLower() switch
    {
        "nearest" => InterpolationMode.Nearest,
        "area"    => InterpolationMode.Area,
        "cubic"   => InterpolationMode.Cubic,
        _         => InterpolationMode.Linear,
    };

    private static Orientation ParseOrientation(string s) =>
        s.Equals("portrait", StringComparison.OrdinalIgnoreCase)
            ? Orientation.Portrait
            : Orientation.Landscape;

    private static ProcessingMode ParseProcessingMode(string s) => s.ToLower() switch
    {
        "stretch" => ProcessingMode.Stretch,
        "fit"     => ProcessingMode.Fit,
        _         => ProcessingMode.Center,
    };
}
