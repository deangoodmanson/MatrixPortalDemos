using LedPortal.Config;

namespace LedPortal.Capture;

public static class CameraFactory
{
    /// <summary>
    /// Create a camera for the current platform.
    /// C# on Raspberry Pi is unusual, so we always use OpenCV (no picamera2 support).
    /// </summary>
    public static ICamera Create(CameraConfig config) => new OpenCvCamera(config);
}
