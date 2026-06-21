using System.Buffers.Binary;
using LedPortal.Config;
using LedPortal.Processing;
using LedPortal.Tests.Fixtures;
using OpenCvSharp;

namespace LedPortal.Tests.Processing;

public class ConvertToRgb565Tests
{
    [Fact]
    public void OutputLength_Is_WidthTimesHeightTimes2()
    {
        using var frame = FrameHelpers.MakeBlackFrame(32, 64);
        var result = ColorProcessor.ConvertToRgb565(frame);
        Assert.Equal(32 * 64 * 2, result.Length);
    }

    [Fact]
    public void BlackFrame_IsAllZeros()
    {
        using var frame = FrameHelpers.MakeBlackFrame();
        var result = ColorProcessor.ConvertToRgb565(frame);
        Assert.All(result, b => Assert.Equal(0, b));
    }

    [Fact]
    public void WhiteFrame_AllBitsSet()
    {
        // White in RGB565 = 0xFFFF (but only 5+6+5=16 bits, so 0b1111111111111111)
        // Actually white (255, 255, 255) → R=31, G=63, B=31 → 0b1111111111111111 = 0xFFFF
        using var frame = FrameHelpers.MakeWhiteFrame(1, 1);
        var result = ColorProcessor.ConvertToRgb565(frame);
        ushort packed = BinaryPrimitives.ReadUInt16LittleEndian(result.AsSpan());
        Assert.Equal(0xFFFF, packed);
    }

    [Fact]
    public void PureRed_Encodes_To_0xF800()
    {
        // Red (BGR: 0, 0, 255) → R=31, G=0, B=0 → 0b1111100000000000 = 0xF800
        using var frame = FrameHelpers.MakeRedFrame(1, 1);
        var result = ColorProcessor.ConvertToRgb565(frame);
        ushort packed = BinaryPrimitives.ReadUInt16LittleEndian(result.AsSpan());
        Assert.Equal(0xF800, packed);
    }

    [Fact]
    public void PureGreen_Encodes_To_0x07E0()
    {
        // Green (BGR: 0, 255, 0) → R=0, G=63, B=0 → 0b0000011111100000 = 0x07E0
        using var frame = FrameHelpers.MakeGreenFrame(1, 1);
        var result = ColorProcessor.ConvertToRgb565(frame);
        ushort packed = BinaryPrimitives.ReadUInt16LittleEndian(result.AsSpan());
        Assert.Equal(0x07E0, packed);
    }

    [Fact]
    public void PureBlue_Encodes_To_0x001F()
    {
        // Blue (BGR: 255, 0, 0) → R=0, G=0, B=31 → 0b0000000000011111 = 0x001F
        using var frame = FrameHelpers.MakeBlueFrame(1, 1);
        var result = ColorProcessor.ConvertToRgb565(frame);
        ushort packed = BinaryPrimitives.ReadUInt16LittleEndian(result.AsSpan());
        Assert.Equal(0x001F, packed);
    }

    [Fact]
    public void Output_Is_LittleEndian()
    {
        // Pure red (0xF800 little-endian) = bytes [0x00, 0xF8]
        using var frame = FrameHelpers.MakeRedFrame(1, 1);
        var result = ColorProcessor.ConvertToRgb565(frame);
        Assert.Equal(0x00, result[0]);
        Assert.Equal(0xF8, result[1]);
    }
}

public class RoundTripTests
{
    // [Theory] + [InlineData] = pytest @pytest.mark.parametrize
    [Theory]
    [InlineData(0,   0,   255, "red")]
    [InlineData(0,   255, 0,   "green")]
    [InlineData(255, 0,   0,   "blue")]
    public void PrimaryColors_SurviveRoundTrip_WithQuantizationTolerance(
        byte b, byte g, byte r, string label)
    {
        // RGB565 uses 5/6/5 bits, so low-order bits are lost.
        // Round-trip should be within rounding error: ≤7 for R/B, ≤3 for G.
        using var original = new Mat(1, 1, MatType.CV_8UC3, new Scalar(b, g, r));
        var bytes = ColorProcessor.ConvertToRgb565(original);
        using var restored = ColorProcessor.Rgb565ToBgr(bytes, 1, 1);

        var px = restored.At<Vec3b>(0, 0);
        Assert.True(Math.Abs(px.Item2 - r) <= 8, $"{label} red channel out of tolerance");
        Assert.True(Math.Abs(px.Item1 - g) <= 4, $"{label} green channel out of tolerance");
        Assert.True(Math.Abs(px.Item0 - b) <= 8, $"{label} blue channel out of tolerance");
    }
}

public class GrayscaleTests
{
    [Fact]
    public void ApplyGrayscale_OutputIsBgr()
    {
        using var frame = FrameHelpers.MakeRedFrame(4, 4);
        using var result = ColorProcessor.ApplyGrayscale(frame);
        Assert.Equal(MatType.CV_8UC3, result.Type());
    }

    [Fact]
    public void ApplyGrayscale_AllChannelsEqual()
    {
        using var frame = FrameHelpers.MakeRedFrame(1, 1);
        using var result = ColorProcessor.ApplyGrayscale(frame);
        var px = result.At<Vec3b>(0, 0);
        Assert.Equal(px.Item0, px.Item1);
        Assert.Equal(px.Item1, px.Item2);
    }
}

public class MirrorTests
{
    [Fact]
    public void ApplyMirror_Landscape_FlipsHorizontally()
    {
        using var frame = new Mat(1, 2, MatType.CV_8UC3);
        frame.At<Vec3b>(0, 0) = new Vec3b(255, 0, 0);  // blue left
        frame.At<Vec3b>(0, 1) = new Vec3b(0, 0, 255);  // red right
        using var result = ColorProcessor.ApplyMirror(frame, Orientation.Landscape);
        Assert.Equal(new Vec3b(0, 0, 255), result.At<Vec3b>(0, 0));
        Assert.Equal(new Vec3b(255, 0, 0), result.At<Vec3b>(0, 1));
    }
}

public class BrightnessLimitTests
{
    [Fact]
    public void ApplyBrightnessLimit_255_ReturnsOriginal()
    {
        using var frame = FrameHelpers.MakeWhiteFrame(1, 1);
        var result = ColorProcessor.ApplyBrightnessLimit(frame, 255);
        Assert.Same(frame, result);
    }

    [Fact]
    public void ApplyBrightnessLimit_64_ClipsAbove64()
    {
        using var frame = FrameHelpers.MakeWhiteFrame(1, 1);
        using var result = ColorProcessor.ApplyBrightnessLimit(frame, 64);
        var px = result.At<Vec3b>(0, 0);
        Assert.True(px.Item0 <= 64);
        Assert.True(px.Item1 <= 64);
        Assert.True(px.Item2 <= 64);
    }

    [Fact]
    public void ApplyBrightnessLimit_DoesNotAffectPixelsBelowThreshold()
    {
        using var frame = new Mat(1, 1, MatType.CV_8UC3, new Scalar(30, 30, 30));
        using var result = ColorProcessor.ApplyBrightnessLimit(frame, 64);
        var px = result.At<Vec3b>(0, 0);
        Assert.Equal(30, px.Item0);
    }
}
