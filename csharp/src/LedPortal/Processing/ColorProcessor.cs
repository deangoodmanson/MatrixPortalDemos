using System.Buffers.Binary;
using LedPortal.Config;
using OpenCvSharp;

namespace LedPortal.Processing;

public static class ColorProcessor
{
    // Gamma LUT built once at type-initialization time (thread-safe in .NET).
    // Inverse sRGB: maps linear LED brightness to perceptually correct preview.
    private static readonly byte[] _gammaLut = BuildGammaLut(2.2);

    // ── RGB565 encoding ────────────────────────────────────────────────────

    /// <summary>
    /// Convert a BGR Mat to RGB565 bytes (4096 bytes for a 64×32 frame).
    ///
    /// RGB565 packing:
    ///   bits 15-11 = Red   (5 bits, >> 3)
    ///   bits 10-5  = Green (6 bits, >> 2)
    ///   bits  4-0  = Blue  (5 bits, >> 3)
    ///
    /// BinaryPrimitives.WriteUInt16LittleEndian replaces numpy's dtype("&lt;u2").tobytes().
    /// It is explicit about endianness and correct on any-endian hardware.
    /// </summary>
    public static byte[] ConvertToRgb565(Mat bgrFrame)
    {
        int width = bgrFrame.Cols;
        int height = bgrFrame.Rows;
        var output = new byte[width * height * 2];
        var outSpan = output.AsSpan();

        // Convert BGR → RGB in a temporary Mat
        using var rgb = new Mat();
        Cv2.CvtColor(bgrFrame, rgb, ColorConversionCodes.BGR2RGB);

        for (int y = 0; y < height; y++)
        {
            for (int x = 0; x < width; x++)
            {
                var px = rgb.At<Vec3b>(y, x);
                ushort r = (ushort)((px.Item0 >> 3) & 0x1F);   // 5 bits
                ushort g = (ushort)((px.Item1 >> 2) & 0x3F);   // 6 bits
                ushort b = (ushort)((px.Item2 >> 3) & 0x1F);   // 5 bits
                ushort rgb565 = (ushort)((r << 11) | (g << 5) | b);

                int offset = (y * width + x) * 2;
                BinaryPrimitives.WriteUInt16LittleEndian(outSpan[offset..], rgb565);
            }
        }

        return output;
    }

    /// <summary>Convert RGB565 bytes back to a BGR Mat (for debugging/round-trip tests).</summary>
    public static Mat Rgb565ToBgr(ReadOnlySpan<byte> data, int width, int height)
    {
        var mat = new Mat(height, width, MatType.CV_8UC3);
        for (int y = 0; y < height; y++)
        {
            for (int x = 0; x < width; x++)
            {
                int offset = (y * width + x) * 2;
                ushort rgb565 = BinaryPrimitives.ReadUInt16LittleEndian(data[offset..]);

                byte r = (byte)(((rgb565 >> 11) & 0x1F) << 3);
                byte g = (byte)(((rgb565 >> 5) & 0x3F) << 2);
                byte b = (byte)((rgb565 & 0x1F) << 3);

                mat.At<Vec3b>(y, x) = new Vec3b(b, g, r);  // BGR order
            }
        }
        return mat;
    }

    // ── Effects ────────────────────────────────────────────────────────────

    /// <summary>
    /// Convert to grayscale and return as BGR (all channels equal).
    /// Maintains pipeline compatibility — everything stays BGR.
    /// </summary>
    public static Mat ApplyGrayscale(Mat frame)
    {
        using var gray = new Mat();
        var result = new Mat();
        Cv2.CvtColor(frame, gray, ColorConversionCodes.BGR2GRAY);
        Cv2.CvtColor(gray, result, ColorConversionCodes.GRAY2BGR);
        return result;
    }

    /// <summary>
    /// Flip left-to-right as seen by the viewer, respecting orientation.
    /// In portrait mode the buffer is rotated 90° CW, so a horizontal flip
    /// in buffer-space appears as a vertical flip on screen. We use flipCode=0
    /// (vertical in the buffer) to get the correct viewer-space mirror.
    /// </summary>
    public static Mat ApplyMirror(Mat frame, Orientation orientation)
    {
        var result = new Mat();
        // FlipMode.X = flip around X-axis (vertical flip, flipCode=0)
        // FlipMode.Y = flip around Y-axis (horizontal flip, flipCode=1)
        FlipMode flipMode = orientation == Orientation.Portrait ? FlipMode.X : FlipMode.Y;
        Cv2.Flip(frame, result, flipMode);
        return result;
    }

    /// <summary>
    /// Clip all channels to maxBrightness.
    /// Use maxBrightness=64 (~25%) for USB-only power to prevent brownouts.
    /// </summary>
    public static Mat ApplyBrightnessLimit(Mat frame, int maxBrightness)
    {
        if (maxBrightness >= 255)
            return frame;

        var result = new Mat();
        Cv2.Min(frame, new Scalar(maxBrightness, maxBrightness, maxBrightness), result);
        return result;
    }

    /// <summary>
    /// Apply gamma correction via a pre-built 256-entry LUT.
    /// The LUT maps input → (input/255)^(1/gamma) * 255.
    /// </summary>
    public static Mat ApplyGammaCorrection(Mat frame, double gamma)
    {
        var lut = gamma == 2.2 ? _gammaLut : BuildGammaLut(gamma);
        using var lutMat = Mat.FromArray(lut);
        var result = new Mat();
        Cv2.LUT(frame, lutMat, result);
        return result;
    }

    // Expose the default gamma LUT for preview rendering
    internal static byte[] GammaLut => _gammaLut;

    private static byte[] BuildGammaLut(double gamma)
    {
        double invGamma = 1.0 / gamma;
        var lut = new byte[256];
        for (int i = 0; i < 256; i++)
            lut[i] = (byte)Math.Round(Math.Pow(i / 255.0, invGamma) * 255.0);
        return lut;
    }
}
