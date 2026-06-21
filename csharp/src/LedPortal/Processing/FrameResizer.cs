using LedPortal.Config;
using OpenCvSharp;

namespace LedPortal.Processing;

public static class FrameResizer
{
    /// <summary>
    /// Crop and resize a frame to matrix dimensions.
    ///
    /// Orientations:
    ///   Landscape — target is 64×32 (no rotation)
    ///   Portrait  — target is 32×64 before rotation; rotated 90° CW to produce 64×32
    ///
    /// Processing modes:
    ///   Center  — center crop preserving aspect ratio (clips edges)
    ///   Stretch — distort to fit exactly (ignores aspect ratio)
    ///   Fit     — letterbox with black bars (maintains aspect ratio)
    /// </summary>
    public static Mat ResizeFrame(
        Mat frame,
        MatrixConfig matrix,
        ProcessingConfig? processing = null,
        Orientation? orientationOverride = null,
        ProcessingMode? modeOverride = null)
    {
        var orientation = orientationOverride ?? processing?.Orientation ?? Orientation.Landscape;
        var mode = modeOverride ?? processing?.ProcessingMode ?? ProcessingMode.Center;
        var interp = ToOpenCvInterp(processing?.Interpolation ?? InterpolationMode.Linear);

        int targetW = matrix.Width;
        int targetH = matrix.Height;

        // For portrait, swap target dimensions BEFORE processing, then rotate after.
        // This ensures the rotated result matches the physical display size.
        if (orientation == Orientation.Portrait)
            (targetW, targetH) = (targetH, targetW);

        Mat processed = mode switch
        {
            ProcessingMode.Stretch => ResizeStretch(frame, targetW, targetH, interp),
            ProcessingMode.Fit     => ResizeLetterbox(frame, targetW, targetH, interp),
            _                      => ResizeCenterCrop(frame, targetW, targetH, interp),
        };

        // C# switch expression is exhaustive — the compiler warns if a new enum value
        // is added without a matching arm. Python's dict.get() would silently return None.

        if (orientation == Orientation.Portrait)
        {
            var rotated = new Mat();
            Cv2.Rotate(processed, rotated, RotateFlags.Rotate90Clockwise);
            processed.Dispose();
            return rotated;
        }

        return processed;
    }

    private static Mat ResizeCenterCrop(Mat frame, int targetW, int targetH, InterpolationFlags interp)
    {
        int h = frame.Rows, w = frame.Cols;
        double targetAspect = (double)targetW / targetH;
        double srcAspect = (double)w / h;

        Mat cropped;
        if (srcAspect > targetAspect)
        {
            // Source is wider — crop left and right
            int newW = (int)(h * targetAspect);
            int startX = (w - newW) / 2;
            cropped = new Mat(frame, new Rect(startX, 0, newW, h));
        }
        else
        {
            // Source is taller — crop top and bottom
            int newH = (int)(w / targetAspect);
            int startY = (h - newH) / 2;
            cropped = new Mat(frame, new Rect(0, startY, w, newH));
        }

        var result = new Mat();
        Cv2.Resize(cropped, result, new Size(targetW, targetH), interpolation: interp);
        cropped.Dispose();
        return result;
    }

    private static Mat ResizeStretch(Mat frame, int targetW, int targetH, InterpolationFlags interp)
    {
        var result = new Mat();
        Cv2.Resize(frame, result, new Size(targetW, targetH), interpolation: interp);
        return result;
    }

    private static Mat ResizeLetterbox(Mat frame, int targetW, int targetH, InterpolationFlags interp)
    {
        int h = frame.Rows, w = frame.Cols;
        double scale = Math.Min((double)targetW / w, (double)targetH / h);
        int newW = (int)(w * scale);
        int newH = (int)(h * scale);

        using var resized = new Mat();
        Cv2.Resize(frame, resized, new Size(newW, newH), interpolation: interp);

        // Create black canvas and center the resized image
        var canvas = Mat.Zeros(targetH, targetW, MatType.CV_8UC3);
        int xOff = (targetW - newW) / 2;
        int yOff = (targetH - newH) / 2;
        var roi = new Mat(canvas, new Rect(xOff, yOff, newW, newH));
        resized.CopyTo(roi);
        roi.Dispose();
        return canvas;
    }

    private static InterpolationFlags ToOpenCvInterp(InterpolationMode mode) => mode switch
    {
        InterpolationMode.Nearest => InterpolationFlags.Nearest,
        InterpolationMode.Area    => InterpolationFlags.Area,
        InterpolationMode.Cubic   => InterpolationFlags.Cubic,
        _                         => InterpolationFlags.Linear,
    };
}
