using LedPortal.Config;
using LedPortal.Processing;
using LedPortal.Tests.Fixtures;

namespace LedPortal.Tests.Processing;

public class TestPatternsTests
{
    private static MatrixConfig Matrix => FrameHelpers.StandardMatrix;

    [Fact]
    public void GradientPattern_OutputLength_IsFrameSizeBytes()
    {
        var result = TestPatterns.CreateGradientPattern(Matrix);
        Assert.Equal(Matrix.FrameSizeBytes, result.Length);
    }

    [Fact]
    public void ColorBars_OutputLength_IsFrameSizeBytes()
    {
        var result = TestPatterns.CreateColorBars(Matrix);
        Assert.Equal(Matrix.FrameSizeBytes, result.Length);
    }

    [Fact]
    public void SolidBlack_IsAllZeros()
    {
        var result = TestPatterns.CreateSolidColor(Matrix, new OpenCvSharp.Vec3b(0, 0, 0));
        Assert.All(result, b => Assert.Equal(0, b));
    }

    [Fact]
    public void SolidWhite_IsNotAllZeros()
    {
        var result = TestPatterns.CreateSolidColor(Matrix, new OpenCvSharp.Vec3b(255, 255, 255));
        Assert.Contains(result, b => b != 0);
    }

    [Fact]
    public void Checkerboard_OutputLength_IsFrameSizeBytes()
    {
        var result = TestPatterns.CreateCheckerboard(Matrix);
        Assert.Equal(Matrix.FrameSizeBytes, result.Length);
    }

    [Fact]
    public void Checkerboard_HasBothColors()
    {
        var black = TestPatterns.CreateSolidColor(Matrix, new OpenCvSharp.Vec3b(0, 0, 0));
        var checker = TestPatterns.CreateCheckerboard(Matrix);

        // Checkerboard should differ from a solid-black frame
        bool differs = false;
        for (int i = 0; i < checker.Length; i++)
            if (checker[i] != black[i]) { differs = true; break; }
        Assert.True(differs);
    }

    [Fact]
    public void GradientPattern_MaxBrightness_Is_AtMost64()
    {
        // USB power safety: gradient uses max brightness 64 (~25%)
        // Round-trip through RGB565 decoder to check
        var result = TestPatterns.CreateGradientPattern(Matrix);
        using var decoded = LedPortal.Processing.ColorProcessor.Rgb565ToBgr(result, Matrix.Width, Matrix.Height);
        for (int y = 0; y < decoded.Rows; y++)
            for (int x = 0; x < decoded.Cols; x++)
            {
                var px = decoded.At<OpenCvSharp.Vec3b>(y, x);
                // Each channel should be at most ~64 (some rounding from RGB565 encoding)
                Assert.True(px.Item0 <= 72, $"Blue channel too bright at ({x},{y}): {px.Item0}");
                Assert.True(px.Item1 <= 72, $"Green channel too bright at ({x},{y}): {px.Item1}");
                Assert.True(px.Item2 <= 72, $"Red channel too bright at ({x},{y}): {px.Item2}");
            }
    }
}
