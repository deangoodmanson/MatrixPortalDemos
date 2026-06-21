using LedPortal.Config;
using LedPortal.Exceptions;
using OpenCvSharp;

namespace LedPortal.Capture;

/// <summary>
/// Camera implementation using OpenCV VideoCapture.
/// Works on macOS, Linux, and Windows with any USB camera.
/// </summary>
public sealed class OpenCvCamera : ICamera
{
    private readonly CameraConfig _config;
    private VideoCapture? _cap;
    private int _actualIndex;

    public OpenCvCamera(CameraConfig config) => (_config, _actualIndex) = (config, config.Index);

    public bool IsOpen => _cap?.IsOpened() ?? false;
    public string CameraType => "opencv";

    public void Open()
    {
        _cap = new VideoCapture(_config.Index);

        if (!_cap.IsOpened())
        {
            // Try indices 1–4 if index 0 failed
            if (_config.Index == 0)
            {
                Console.WriteLine("Camera index 0 failed, trying other indices...");
                for (int i = 1; i < 5; i++)
                {
                    _cap.Release();
                    _cap = new VideoCapture(i);
                    if (_cap.IsOpened())
                    {
                        Console.WriteLine($"Found camera at index {i}");
                        _actualIndex = i;
                        break;
                    }
                }
            }

            if (!_cap.IsOpened())
                throw new CameraNotFoundException(
                    $"Failed to open camera at index {_config.Index}");
        }

        // Set resolution if explicitly requested
        if (_config.Width > 0 && _config.Height > 0)
        {
            _cap.Set(VideoCaptureProperties.FrameWidth, _config.Width);
            _cap.Set(VideoCaptureProperties.FrameHeight, _config.Height);

            // Validate — some cameras silently ignore unsupported resolutions
            bool ok = _cap.Read(new Mat());
            if (!ok)
            {
                Console.WriteLine(
                    $"Warning: Camera doesn't support {_config.Width}×{_config.Height}, using native resolution.");
                _cap.Release();
                _cap = new VideoCapture(_actualIndex);
                if (!_cap.IsOpened())
                    throw new CameraNotFoundException($"Failed to reopen camera at index {_actualIndex}");
            }
        }
        else
        {
            // Validate at native resolution
            using var test = new Mat();
            if (!_cap.Read(test) || test.Empty())
                throw new CameraNotFoundException(
                    $"Camera at index {_actualIndex} cannot capture frames");
        }
    }

    public void Close()
    {
        _cap?.Release();
        _cap?.Dispose();
        _cap = null;
    }

    public Mat Capture()
    {
        if (_cap is null || !_cap.IsOpened())
            throw new CameraCaptureFailed("Camera is not open");

        var frame = new Mat();
        if (!_cap.Read(frame) || frame.Empty())
            throw new CameraCaptureFailed("Failed to read frame from camera");

        return frame;
    }

    public IReadOnlyDictionary<string, object> GetCameraInfo()
    {
        if (_cap is null || !_cap.IsOpened())
            return new Dictionary<string, object>
            {
                ["type"] = "opencv",
                ["index"] = _actualIndex,
                ["status"] = "not_opened",
            };

        int width = (int)_cap.Get(VideoCaptureProperties.FrameWidth);
        int height = (int)_cap.Get(VideoCaptureProperties.FrameHeight);
        double fps = _cap.Get(VideoCaptureProperties.Fps);

        return new Dictionary<string, object>
        {
            ["type"] = "opencv",
            ["index"] = _actualIndex,
            ["resolution"] = $"{width}x{height}",
            ["width"] = width,
            ["height"] = height,
            ["fps"] = fps > 0 ? fps : "unknown",
            ["requested_resolution"] = $"{_config.Width}x{_config.Height}",
        };
    }

    public void Dispose() => Close();
}
