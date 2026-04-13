using LedPortal.Processing;
using LedPortal.Tests.Fixtures;
using OpenCvSharp;

namespace LedPortal.Tests.Processing;

public class ZoomCropperTests
{
    [Fact]
    public void Zoom_1_0_ReturnsSameObject()
    {
        using var frame = FrameHelpers.MakeLandscapeSource();
        var result = ZoomCropper.ApplyZoomCrop(frame, 1.0);
        // No allocation for no-op zoom
        Assert.Same(frame, result);
    }

    [Theory]
    [InlineData(0.5,  960, 540)]
    [InlineData(0.75, 1440, 810)]
    [InlineData(0.25, 480, 270)]
    public void Zoom_ScalesCropCorrectly(double zoom, int expectedW, int expectedH)
    {
        using var frame = FrameHelpers.MakeSolidFrame(1080, 1920, new Vec3b(100, 100, 100));
        using var result = ZoomCropper.ApplyZoomCrop(frame, zoom);
        Assert.Equal(expectedW, result.Cols);
        Assert.Equal(expectedH, result.Rows);
    }

    [Fact]
    public void Zoom_IsCenteredOnFrame()
    {
        // Create frame where edges are red and center is blue.
        using var frame = new Mat(100, 100, MatType.CV_8UC3, Scalar.Red);
        // Paint center 50×50 blue
        var centerRoi = new Mat(frame, new Rect(25, 25, 50, 50));
        centerRoi.SetTo(Scalar.Blue);
        centerRoi.Dispose();

        using var result = ZoomCropper.ApplyZoomCrop(frame, 0.5);
        // Center pixel of result should be blue
        var center = result.At<Vec3b>(result.Rows / 2, result.Cols / 2);
        Assert.Equal(255, center.Item0);  // Blue channel (BGR)
        Assert.Equal(0, center.Item2);    // Red channel
    }

    [Fact]
    public void Zoom_GreaterThan1_ReturnsSameObject()
    {
        using var frame = FrameHelpers.MakeBlackFrame();
        var result = ZoomCropper.ApplyZoomCrop(frame, 1.5);
        Assert.Same(frame, result);
    }
}
