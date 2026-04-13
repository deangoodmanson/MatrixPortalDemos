using OpenCvSharp;

namespace LedPortal.Processing;

public static class ZoomCropper
{
    /// <summary>
    /// Crop frame to a centered percentage (zoom-in effect).
    /// zoom = 1.0 → no crop (100%); zoom = 0.5 → center 50% (2× zoom).
    /// Returns a zero-copy submatrix sharing memory with the original.
    /// </summary>
    public static Mat ApplyZoomCrop(Mat frame, double zoom)
    {
        if (zoom >= 1.0)
            return frame;  // fast path — no allocation

        int newW = (int)(frame.Cols * zoom);
        int newH = (int)(frame.Rows * zoom);
        int startX = (frame.Cols - newW) / 2;
        int startY = (frame.Rows - newH) / 2;

        // Mat(Mat, Rect) creates a zero-copy submatrix — equivalent to
        // numpy's frame[y1:y2, x1:x2]. The result shares memory with 'frame'.
        return new Mat(frame, new Rect(startX, startY, newW, newH));
    }
}
