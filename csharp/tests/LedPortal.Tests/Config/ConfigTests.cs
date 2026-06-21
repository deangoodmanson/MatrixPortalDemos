using LedPortal.Config;
using LedPortal.Exceptions;

namespace LedPortal.Tests.Config;

// xUnit [Fact] = plain pytest test function
// xUnit [Theory] + [InlineData] = pytest @pytest.mark.parametrize

public class DefaultsTests
{
    [Fact]
    public void DefaultMatrix_Is_64x32()
    {
        var config = AppConfig.CreateDefault();
        Assert.Equal(64, config.Matrix.Width);
        Assert.Equal(32, config.Matrix.Height);
    }

    [Fact]
    public void DefaultTransport_BaudRate_Is_4M()
    {
        var config = AppConfig.CreateDefault();
        Assert.Equal(4_000_000, config.Transport.BaudRate);
    }

    [Fact]
    public void FrameSizeBytes_Is_4096_For_64x32()
    {
        var matrix = new MatrixConfig(64, 32);
        Assert.Equal(4096, matrix.FrameSizeBytes);
    }

    [Fact]
    public void FrameTimeMs_IsCorrect_For_30fps()
    {
        var config = AppConfig.CreateDefault();
        Assert.Equal(1000.0 / 30, config.FrameTimeMs, precision: 5);
    }

    [Fact]
    public void DefaultProcessing_Is_LandscapeCenter()
    {
        var config = AppConfig.CreateDefault();
        Assert.Equal(Orientation.Landscape, config.Processing.Orientation);
        Assert.Equal(ProcessingMode.Center, config.Processing.ProcessingMode);
    }

    [Fact]
    public void DefaultMaxBrightness_Is_255()
    {
        var config = AppConfig.CreateDefault();
        Assert.Equal(255, config.Processing.MaxBrightness);
    }
}

public class LoadConfigTests
{
    [Fact]
    public void LoadNull_ReturnsDefaults()
    {
        var config = ConfigLoader.Load(null);
        Assert.Equal(64, config.Matrix.Width);
        Assert.Equal(32, config.Matrix.Height);
    }

    [Fact]
    public void LoadMissingFile_Throws_ConfigNotFoundException()
    {
        // Assert.Throws replaces pytest.raises
        Assert.Throws<ConfigNotFoundException>(() =>
            ConfigLoader.Load("/nonexistent/path/config.yaml"));
    }

    [Fact]
    public void LoadInvalidYaml_Throws_ConfigValidationException()
    {
        var path = Path.GetTempFileName();
        try
        {
            File.WriteAllText(path, "not: valid: yaml: ::::");
            Assert.Throws<ConfigValidationException>(() => ConfigLoader.Load(path));
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void LoadPartialYaml_OverridesOnlySpecifiedFields()
    {
        var yaml = "target_fps: 15\n";
        var path = Path.GetTempFileName();
        try
        {
            File.WriteAllText(path, yaml);
            var config = ConfigLoader.Load(path);
            Assert.Equal(15, config.TargetFps);
            // Unspecified fields retain defaults
            Assert.Equal(64, config.Matrix.Width);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void LoadMacYaml_OverridesFps()
    {
        var yaml = @"target_fps: 30
camera:
  width: 640
  height: 480
  index: 0
";
        var path = Path.GetTempFileName();
        try
        {
            File.WriteAllText(path, yaml);
            var config = ConfigLoader.Load(path);
            Assert.Equal(30, config.TargetFps);
            Assert.Equal(640, config.Camera.Width);
            Assert.Equal(480, config.Camera.Height);
        }
        finally { File.Delete(path); }
    }
}

public class RecordMutationTests
{
    [Fact]
    public void WithExpression_ProducesNewRecord_LeavingOriginalUnchanged()
    {
        // This test demonstrates the key C# teaching moment:
        // `with` creates a new record rather than mutating the original.
        var original = AppConfig.CreateDefault();
        var modified = original with { TargetFps = 60 };

        Assert.Equal(30, original.TargetFps);  // original unchanged
        Assert.Equal(60, modified.TargetFps);  // new record has new value
    }

    [Fact]
    public void NestedWithExpression_UpdatesNestedRecord()
    {
        var config = AppConfig.CreateDefault();
        var updated = config with
        {
            Processing = config.Processing with { Orientation = Orientation.Portrait }
        };

        Assert.Equal(Orientation.Landscape, config.Processing.Orientation);
        Assert.Equal(Orientation.Portrait, updated.Processing.Orientation);
    }
}

public class SaveLoadRoundTripTests
{
    [Fact]
    public void SaveAndLoad_RoundTrips_TargetFps()
    {
        var original = AppConfig.CreateDefault() with { TargetFps = 24 };
        var path = Path.GetTempFileName();
        try
        {
            ConfigLoader.Save(original, path);
            var loaded = ConfigLoader.Load(path);
            Assert.Equal(24, loaded.TargetFps);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void SaveAndLoad_RoundTrips_Orientation()
    {
        var original = AppConfig.CreateDefault() with
        {
            Processing = AppConfig.CreateDefault().Processing with { Orientation = Orientation.Portrait }
        };
        var path = Path.GetTempFileName();
        try
        {
            ConfigLoader.Save(original, path);
            var loaded = ConfigLoader.Load(path);
            Assert.Equal(Orientation.Portrait, loaded.Processing.Orientation);
        }
        finally { File.Delete(path); }
    }
}
