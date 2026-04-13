using LedPortal.Config;
using OpenCvSharp;

namespace LedPortal.Processing;

public static class TestPatterns
{
    private const int UsbSafeMaxBrightness = 64;  // ~25% — prevents USB brownouts

    /// <summary>
    /// Gradient test pattern: red gradient horizontally, green vertically, blue constant.
    /// Uses low brightness to avoid power issues when matrix is USB-only powered.
    /// </summary>
    public static byte[] CreateGradientPattern(MatrixConfig matrix)
    {
        using var frame = new Mat(matrix.Height, matrix.Width, MatType.CV_8UC3, Scalar.Black);

        for (int y = 0; y < matrix.Height; y++)
        {
            byte green = (byte)(y * UsbSafeMaxBrightness / matrix.Height);
            for (int x = 0; x < matrix.Width; x++)
            {
                byte red = (byte)(x * UsbSafeMaxBrightness / matrix.Width);
                frame.At<Vec3b>(y, x) = new Vec3b(UsbSafeMaxBrightness / 2, green, red);  // BGR
            }
        }

        return ColorProcessor.ConvertToRgb565(frame);
    }

    /// <summary>
    /// Standard 8-bar color bars: white, yellow, cyan, green, magenta, red, blue, black.
    /// Colors in BGR order (OpenCV convention).
    /// </summary>
    public static byte[] CreateColorBars(MatrixConfig matrix)
    {
        // Colors in BGR format
        Vec3b[] colors =
        [
            new(255, 255, 255), // White
            new(0,   255, 255), // Yellow
            new(255, 255, 0),   // Cyan
            new(0,   255, 0),   // Green
            new(255, 0,   255), // Magenta
            new(0,   0,   255), // Red
            new(255, 0,   0),   // Blue
            new(0,   0,   0),   // Black
        ];

        using var frame = new Mat(matrix.Height, matrix.Width, MatType.CV_8UC3, Scalar.Black);
        int barWidth = matrix.Width / colors.Length;

        for (int i = 0; i < colors.Length; i++)
        {
            int x1 = i * barWidth;
            int x2 = (i < colors.Length - 1) ? (i + 1) * barWidth : matrix.Width;
            var roi = new Mat(frame, new Rect(x1, 0, x2 - x1, matrix.Height));
            roi.SetTo(new Scalar(colors[i].Item0, colors[i].Item1, colors[i].Item2));
            roi.Dispose();
        }

        return ColorProcessor.ConvertToRgb565(frame);
    }

    /// <summary>Fill the entire frame with a single BGR color.</summary>
    public static byte[] CreateSolidColor(MatrixConfig matrix, Vec3b bgrColor)
    {
        using var frame = new Mat(
            matrix.Height, matrix.Width, MatType.CV_8UC3,
            new Scalar(bgrColor.Item0, bgrColor.Item1, bgrColor.Item2));
        return ColorProcessor.ConvertToRgb565(frame);
    }

    /// <summary>Checkerboard pattern with two alternating BGR colors.</summary>
    public static byte[] CreateCheckerboard(
        MatrixConfig matrix,
        int cellSize = 4,
        Vec3b? color1 = null,
        Vec3b? color2 = null)
    {
        var c1 = color1 ?? new Vec3b(0, 0, 0);
        var c2 = color2 ?? new Vec3b(255, 255, 255);

        using var frame = new Mat(matrix.Height, matrix.Width, MatType.CV_8UC3, Scalar.Black);

        for (int y = 0; y < matrix.Height; y++)
        {
            for (int x = 0; x < matrix.Width; x++)
            {
                bool even = ((x / cellSize) + (y / cellSize)) % 2 == 0;
                frame.At<Vec3b>(y, x) = even ? c1 : c2;
            }
        }

        return ColorProcessor.ConvertToRgb565(frame);
    }
}
