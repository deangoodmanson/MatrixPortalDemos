using LedPortal.Config;
using LedPortal.Processing;
using LedPortal.Tests.Fixtures;
using OpenCvSharp;

namespace LedPortal.Tests.Processing;

public class OutputDimensionsTests
{
    // MemberData with LINQ combinatorics replaces pytest's double-stacked parametrize.
    // This generates every combination of Orientation × ProcessingMode automatically.
    public static IEnumerable<object[]> OrientationAndModeMatrix =>
        from o in Enum.GetValues<Orientation>()
        from m in Enum.GetValues<ProcessingMode>()
        select new object[] { o, m };

    [Theory, MemberData(nameof(OrientationAndModeMatrix))]
    public void AllOrientationModeCombinations_Produce_64x32Output(Orientation o, ProcessingMode m)
    {
        using var frame = FrameHelpers.MakeLandscapeSource();
        var matrix = FrameHelpers.StandardMatrix;
        using var result = FrameResizer.ResizeFrame(frame, matrix,
            new ProcessingConfig(Orientation: o, ProcessingMode: m));

        // Output is always 64×32 regardless of orientation (portrait rotates internally)
        Assert.Equal(64, result.Cols);
        Assert.Equal(32, result.Rows);
    }

    [Fact]
    public void OutputIsBgr()
    {
        using var frame = FrameHelpers.MakeLandscapeSource();
        using var result = FrameResizer.ResizeFrame(frame, FrameHelpers.StandardMatrix);
        Assert.Equal(MatType.CV_8UC3, result.Type());
    }
}

public class CenterCropTests
{
    [Fact]
    public void CenterCrop_WideSource_CropsWidth()
    {
        // Wide source (4:1) → matrix is 2:1 → should crop left/right
        using var wideFrame = FrameHelpers.MakeSolidFrame(100, 400, new Vec3b(128, 128, 128));
        var matrix = FrameHelpers.StandardMatrix;
        using var result = FrameResizer.ResizeFrame(wideFrame, matrix,
            new ProcessingConfig(ProcessingMode: ProcessingMode.Center));
        Assert.Equal(64, result.Cols);
        Assert.Equal(32, result.Rows);
    }

    [Fact]
    public void CenterCrop_TallSource_CropsHeight()
    {
        using var tallFrame = FrameHelpers.MakeSolidFrame(400, 100, new Vec3b(128, 128, 128));
        var matrix = FrameHelpers.StandardMatrix;
        using var result = FrameResizer.ResizeFrame(tallFrame, matrix,
            new ProcessingConfig(ProcessingMode: ProcessingMode.Center));
        Assert.Equal(64, result.Cols);
        Assert.Equal(32, result.Rows);
    }
}

public class LetterboxTests
{
    [Fact]
    public void Fit_WideSource_HasBlackBarsTopAndBottom()
    {
        // Square source (100×100) into 64×32 landscape → should have black bars top/bottom
        using var squareFrame = FrameHelpers.MakeSolidFrame(100, 100, new Vec3b(200, 100, 50));
        var matrix = FrameHelpers.StandardMatrix;
        using var result = FrameResizer.ResizeFrame(squareFrame, matrix,
            new ProcessingConfig(ProcessingMode: ProcessingMode.Fit));
        // Top-left corner should be black (part of letterbox bars)
        var topLeft = result.At<Vec3b>(0, 0);
        Assert.Equal(0, topLeft.Item0);
        Assert.Equal(0, topLeft.Item1);
        Assert.Equal(0, topLeft.Item2);
    }
}

public class StretchTests
{
    [Fact]
    public void Stretch_AlwaysExactlyFillsTarget()
    {
        using var frame = FrameHelpers.MakeSolidFrame(200, 300, new Vec3b(100, 150, 200));
        var matrix = FrameHelpers.StandardMatrix;
        using var result = FrameResizer.ResizeFrame(frame, matrix,
            new ProcessingConfig(ProcessingMode: ProcessingMode.Stretch));
        Assert.Equal(64, result.Cols);
        Assert.Equal(32, result.Rows);
    }
}

public class PortraitTests
{
    [Fact]
    public void Portrait_StillOutputs_64x32()
    {
        using var frame = FrameHelpers.MakeLandscapeSource();
        var matrix = FrameHelpers.StandardMatrix;
        using var result = FrameResizer.ResizeFrame(frame, matrix,
            new ProcessingConfig(Orientation: Orientation.Portrait));
        Assert.Equal(64, result.Cols);
        Assert.Equal(32, result.Rows);
    }
}

public class SmallMatrixTests
{
    [Fact]
    public void SmallMatrix_8x4_ProducesCorrectDimensions()
    {
        using var frame = FrameHelpers.MakeSolidFrame(100, 200, new Vec3b(0, 0, 255));
        var matrix = FrameHelpers.SmallMatrix;
        using var result = FrameResizer.ResizeFrame(frame, matrix);
        Assert.Equal(8, result.Cols);
        Assert.Equal(4, result.Rows);
    }
}
