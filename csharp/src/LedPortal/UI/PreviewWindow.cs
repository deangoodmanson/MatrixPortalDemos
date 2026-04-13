using LedPortal.Config;
using LedPortal.Processing;
using OpenCvSharp;

namespace LedPortal.UI;

public enum PreviewAlgorithm { Squares, Circles, GaussianRaw, GaussianDiffused }

public static class PreviewWindow
{
    public static readonly int[] LedSizeSteps = [25, 50, 75, 100, 125, 150];
    public const int LedSizeDefault = 100;

    public static readonly IReadOnlyDictionary<PreviewAlgorithm, string> AlgorithmLabels =
        new Dictionary<PreviewAlgorithm, string>
        {
            [PreviewAlgorithm.Squares]           = "squares",
            [PreviewAlgorithm.Circles]           = "circles (hard edge, size adjustable with +/-)",
            [PreviewAlgorithm.GaussianRaw]       = "raw panel emulation (gaussian, sigma≈18% cell)",
            [PreviewAlgorithm.GaussianDiffused]  = "diffused panel emulation (gaussian, sigma≈27% cell)",
        };

    // Cached distance grids keyed by (outH, outW, scale) — same as Python's _dist_cache
    private static readonly Dictionary<(int, int, int), float[,]> _distCache = [];

    private const string WindowTitle =
        "[ Camera ] | [ LED Matrix Preview ]    Note: The console must have window focus for keyboard commands.";

    /// <summary>Show the 3-pane preview window (raw camera | matrix frame | LED render).</summary>
    public static void Show(
        Mat originalFrame,
        Mat smallFrame,
        MatrixConfig matrix,
        Orientation orientation,
        ProcessingMode mode,
        double zoomLevel,
        PreviewAlgorithm algorithm,
        int ledSizePct,
        int maxBrightness,
        string demoLabel = "")
    {
        const int scale = 10;

        // Render LED preview pane
        using var enlarged = RenderLedPreview(smallFrame, algorithm, ledSizePct, scale);

        // Scale brightness if below maximum
        Mat ledPane;
        if (maxBrightness < 255)
        {
            ledPane = new Mat();
            enlarged.ConvertTo(ledPane, -1, maxBrightness / 255.0);
        }
        else
        {
            ledPane = enlarged.Clone();
        }

        // Apply gamma LUT to match physical LED panel brightness perception
        using var lutMat = Mat.FromArray(ColorProcessor.GammaLut);
        var gammaPane = new Mat();
        Cv2.LUT(ledPane, lutMat, gammaPane);
        ledPane.Dispose();

        // Rotate LED pane for portrait mode
        if (orientation == Orientation.Portrait)
        {
            var rotated = new Mat();
            Cv2.Rotate(gammaPane, rotated, RotateFlags.Rotate90Counterclockwise);
            gammaPane.Dispose();
            gammaPane = rotated;
        }

        // Scale camera frame to match LED pane height
        int targetH = gammaPane.Rows;
        int camH = originalFrame.Rows, camW = originalFrame.Cols;
        int scaledW = (int)((double)camW * targetH / camH);
        using var camResized = originalFrame.Resize(new Size(scaledW, targetH));

        // Draw capture region rectangle on camera pane
        DrawCaptureRect(camResized, originalFrame, matrix, orientation, mode, zoomLevel, targetH, camH, camW);

        // Draw demo label
        if (!string.IsNullOrEmpty(demoLabel))
        {
            Cv2.PutText(camResized, demoLabel, new Point(10, targetH - 15),
                HersheyFonts.HersheySimplex, 0.7, Scalar.Red, 2, LineTypes.AntiAlias);
        }

        using var combined = new Mat();
        Cv2.HConcat([camResized, gammaPane], combined);
        gammaPane.Dispose();

        Cv2.ImShow(WindowTitle, combined);
        Cv2.WaitKey(1);
    }

    public static void DestroyAll() { Cv2.DestroyAllWindows(); Cv2.WaitKey(1); }

    // ── LED render algorithms ──────────────────────────────────────────────

    public static Mat RenderLedPreview(
        Mat smallFrame,
        PreviewAlgorithm algorithm,
        int ledSizePct,
        int scale = 10,
        Vec3b? bgColor = null)
    {
        int h = smallFrame.Rows, w = smallFrame.Cols;
        int outH = h * scale, outW = w * scale;
        var bg = bgColor ?? new Vec3b(0, 0, 0);
        var bgScalar = new Scalar(bg.Item0, bg.Item1, bg.Item2);

        return algorithm switch
        {
            PreviewAlgorithm.Squares => smallFrame.Resize(
                new Size(outW, outH), interpolation: InterpolationFlags.Nearest),

            PreviewAlgorithm.GaussianRaw =>
                RenderGaussian(smallFrame, outH, outW, scale, sigma: scale * 0.18),

            PreviewAlgorithm.GaussianDiffused =>
                RenderGaussian(smallFrame, outH, outW, scale, sigma: scale * 0.27),

            PreviewAlgorithm.Circles => RenderCircles(
                smallFrame, outH, outW, scale, ledSizePct, bgScalar),

            _ => smallFrame.Resize(new Size(outW, outH), interpolation: InterpolationFlags.Nearest),
        };
    }

    private static Mat RenderGaussian(Mat smallFrame, int outH, int outW, int scale, double sigma)
    {
        int h = smallFrame.Rows, w = smallFrame.Cols;

        // Place each LED as a single bright pixel at its cell centre
        using var dots = new Mat(outH, outW, MatType.CV_32FC3, Scalar.Black);

        for (int row = 0; row < h; row++)
        {
            for (int col = 0; col < w; col++)
            {
                int cy = row * scale + scale / 2;
                int cx = col * scale + scale / 2;
                var px = smallFrame.At<Vec3b>(row, col);
                dots.At<Vec3f>(cy, cx) = new Vec3f(px.Item0, px.Item1, px.Item2);
            }
        }

        // Gaussian blur simulates LED diffuser
        using var blurred = new Mat();
        Cv2.GaussianBlur(dots, blurred, new Size(0, 0), sigma);

        // Normalise: restore peak brightness (2π σ² factor for 2D Gaussian)
        double peakFactor = 2.0 * Math.PI * sigma * sigma;
        using var scaled = new Mat();
        Cv2.Multiply(blurred, new Scalar(peakFactor, peakFactor, peakFactor), scaled);

        var result = new Mat();
        scaled.ConvertTo(result, MatType.CV_8UC3, alpha: 1.0, beta: 0.0);
        // Clip to [0, 255]
        Cv2.Min(result, new Scalar(255, 255, 255), result);
        return result;
    }

    private static Mat RenderCircles(
        Mat smallFrame, int outH, int outW, int scale, int ledSizePct, Scalar bgScalar)
    {
        double half = scale / 2.0;
        double radius = scale * (ledSizePct / 200.0);

        if (radius > half)
            return RenderPainter(smallFrame, outH, outW, scale, radius, bgScalar);

        // Vectorised mask for non-overlapping circles
        using var colored = smallFrame.Resize(new Size(outW, outH), interpolation: InterpolationFlags.Nearest);
        var dist = GetDistGrid(outH, outW, scale);
        var bg = new Mat(outH, outW, MatType.CV_8UC3, bgScalar);

        var result = new Mat(outH, outW, MatType.CV_8UC3);
        for (int y = 0; y < outH; y++)
        {
            for (int x = 0; x < outW; x++)
            {
                result.At<Vec3b>(y, x) = dist[y, x] <= radius
                    ? colored.At<Vec3b>(y, x)
                    : bg.At<Vec3b>(y, x);
            }
        }
        bg.Dispose();
        return result;
    }

    private static Mat RenderPainter(
        Mat smallFrame, int outH, int outW, int scale, double radius, Scalar bgScalar)
    {
        int h = smallFrame.Rows, w = smallFrame.Cols;
        var output = new Mat(outH, outW, MatType.CV_8UC3, bgScalar);
        int rInt = (int)Math.Ceiling(radius);

        for (int row = 0; row < h; row++)
        {
            for (int col = 0; col < w; col++)
            {
                int cx = col * scale + scale / 2;
                int cy = row * scale + scale / 2;
                var px = smallFrame.At<Vec3b>(row, col);
                Cv2.Circle(output, new Point(cx, cy), rInt,
                    new Scalar(px.Item0, px.Item1, px.Item2), thickness: -1);
            }
        }
        return output;
    }

    private static float[,] GetDistGrid(int outH, int outW, int scale)
    {
        var key = (outH, outW, scale);
        if (_distCache.TryGetValue(key, out var cached))
            return cached;

        var dist = new float[outH, outW];
        for (int y = 0; y < outH; y++)
        {
            float dy = (y % scale) - scale / 2.0f;
            for (int x = 0; x < outW; x++)
            {
                float dx = (x % scale) - scale / 2.0f;
                dist[y, x] = MathF.Sqrt(dx * dx + dy * dy);
            }
        }
        _distCache[key] = dist;
        return dist;
    }

    // ── Overlay helpers ────────────────────────────────────────────────────

    public static Mat DrawCountdownOverlay(
        Mat frame, int number, MatrixConfig matrix, Orientation orientation)
    {
        var overlay = frame.Clone();
        string text = number.ToString();

        if (orientation == Orientation.Portrait)
        {
            var textSize = Cv2.GetTextSize(text, HersheyFonts.HersheySimplex, 0.5, 1, out _);
            using var temp = new Mat(textSize.Height + 10, textSize.Width + 10, MatType.CV_8UC3, Scalar.Black);
            Cv2.PutText(temp, text, new Point(5, textSize.Height + 2),
                HersheyFonts.HersheySimplex, 0.5, Scalar.Red, 1, LineTypes.AntiAlias);
            using var rotated = new Mat();
            Cv2.Rotate(temp, rotated, RotateFlags.Rotate90Clockwise);
            int h = rotated.Rows, w = rotated.Cols;
            int yStart = matrix.Height - h - 2;
            int xStart = matrix.Width - w - 2;
            if (yStart >= 0 && xStart >= 0)
            {
                var roi = new Mat(overlay, new Rect(xStart, yStart, w, h));
                rotated.CopyTo(roi);
                roi.Dispose();
            }
        }
        else
        {
            Cv2.PutText(overlay, text, new Point(2, matrix.Height - 4),
                HersheyFonts.HersheySimplex, 0.5, Scalar.Red, 1, LineTypes.AntiAlias);
        }

        return overlay;
    }

    public static Mat DrawTextOverlay(Mat frame, string text, Point position,
        Scalar? color = null, double fontScale = 0.5, int thickness = 1)
    {
        var overlay = frame.Clone();
        Cv2.PutText(overlay, text, position, HersheyFonts.HersheySimplex,
            fontScale, color ?? Scalar.White, thickness, LineTypes.AntiAlias);
        return overlay;
    }

    public static Mat DrawBorder(Mat frame, Scalar? color = null)
    {
        var bordered = frame.Clone();
        var c = color ?? Scalar.Red;
        int h = bordered.Rows, w = bordered.Cols;
        bordered.Row(0).SetTo(c);
        bordered.Row(h - 1).SetTo(c);
        bordered.Col(0).SetTo(c);
        bordered.Col(w - 1).SetTo(c);
        return bordered;
    }

    // ── Private helpers ────────────────────────────────────────────────────

    private static void DrawCaptureRect(
        Mat camResized, Mat original, MatrixConfig matrix,
        Orientation orientation, ProcessingMode mode, double zoom,
        int targetH, int camH, int camW)
    {
        int zoomW, zoomH, zoomX1, zoomY1;
        if (zoom < 1.0)
        {
            zoomW = (int)(camW * zoom);
            zoomH = (int)(camH * zoom);
            zoomX1 = (camW - zoomW) / 2;
            zoomY1 = (camH - zoomH) / 2;
        }
        else
        {
            (zoomW, zoomH, zoomX1, zoomY1) = (camW, camH, 0, 0);
        }

        int x1, y1, x2, y2;
        if (mode == ProcessingMode.Center)
        {
            int tw = orientation == Orientation.Portrait ? matrix.Height : matrix.Width;
            int th = orientation == Orientation.Portrait ? matrix.Width : matrix.Height;
            double targetAspect = (double)tw / th;
            double zoomAspect = (double)zoomW / zoomH;
            if (zoomAspect > targetAspect)
            {
                int innerW = (int)(zoomH * targetAspect);
                int innerX1 = (zoomW - innerW) / 2;
                (x1, y1, x2, y2) = (zoomX1 + innerX1, zoomY1, zoomX1 + innerX1 + innerW, zoomY1 + zoomH);
            }
            else
            {
                int innerH = (int)(zoomW / targetAspect);
                int innerY1 = (zoomH - innerH) / 2;
                (x1, y1, x2, y2) = (zoomX1, zoomY1 + innerY1, zoomX1 + zoomW, zoomY1 + innerY1 + innerH);
            }
        }
        else
        {
            (x1, y1) = (zoomX1, zoomY1);
            (x2, y2) = (zoomX1 + zoomW, zoomY1 + zoomH);
        }

        double s = (double)targetH / camH;
        int px1 = (int)(x1 * s), py1 = (int)(y1 * s);
        int px2 = Math.Min((int)(x2 * s), camResized.Cols) - 1;
        int py2 = (int)(y2 * s) - 1;
        Cv2.Rectangle(camResized, new Point(px1, py1), new Point(px2, py2), Scalar.Blue, 1);
    }
}
