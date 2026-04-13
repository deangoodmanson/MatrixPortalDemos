using OpenCvSharp;

namespace LedPortal.Capture;

/// <summary>
/// Camera abstraction. IDisposable replaces Python's __enter__/__exit__.
/// The `using` statement guarantees Dispose() runs even on exception,
/// regardless of GC timing — important for camera handles.
/// </summary>
public interface ICamera : IDisposable
{
    bool IsOpen { get; }
    string CameraType { get; }
    IReadOnlyDictionary<string, object> GetCameraInfo();
    void Open();
    void Close();

    /// <summary>Capture a frame. Returns BGR Mat.</summary>
    Mat Capture();
}
