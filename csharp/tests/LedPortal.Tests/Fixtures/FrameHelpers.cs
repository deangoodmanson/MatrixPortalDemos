using LedPortal.Config;
using OpenCvSharp;

namespace LedPortal.Tests.Fixtures;

/// <summary>
/// Shared test helpers — equivalent to pytest's conftest.py fixtures.
/// Static methods instead of pytest fixtures; called directly in test constructors.
/// </summary>
public static class FrameHelpers
{
    public static MatrixConfig StandardMatrix => new(64, 32);
    public static MatrixConfig SmallMatrix => new(8, 4);

    /// <summary>Create a solid-color BGR Mat.</summary>
    public static Mat MakeSolidFrame(int height, int width, Vec3b color) =>
        new Mat(height, width, MatType.CV_8UC3,
            new Scalar(color.Item0, color.Item1, color.Item2));

    /// <summary>Black frame.</summary>
    public static Mat MakeBlackFrame(int height = 32, int width = 64) =>
        MakeSolidFrame(height, width, new Vec3b(0, 0, 0));

    /// <summary>White frame.</summary>
    public static Mat MakeWhiteFrame(int height = 32, int width = 64) =>
        MakeSolidFrame(height, width, new Vec3b(255, 255, 255));

    /// <summary>Pure red frame (BGR: 0, 0, 255).</summary>
    public static Mat MakeRedFrame(int height = 32, int width = 64) =>
        MakeSolidFrame(height, width, new Vec3b(0, 0, 255));

    /// <summary>Pure green frame (BGR: 0, 255, 0).</summary>
    public static Mat MakeGreenFrame(int height = 32, int width = 64) =>
        MakeSolidFrame(height, width, new Vec3b(0, 255, 0));

    /// <summary>Pure blue frame (BGR: 255, 0, 0).</summary>
    public static Mat MakeBlueFrame(int height = 32, int width = 64) =>
        MakeSolidFrame(height, width, new Vec3b(255, 0, 0));

    /// <summary>Landscape (1920×1080) source frame for resize tests.</summary>
    public static Mat MakeLandscapeSource() =>
        MakeSolidFrame(1080, 1920, new Vec3b(128, 64, 32));

    /// <summary>Portrait (1080×1920) source frame for resize tests.</summary>
    public static Mat MakePortraitSource() =>
        MakeSolidFrame(1920, 1080, new Vec3b(32, 64, 128));
}
