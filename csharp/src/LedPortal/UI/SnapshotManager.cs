using LedPortal.Config;
using LedPortal.Processing;
using OpenCvSharp;

namespace LedPortal.UI;

public class SnapshotManager
{
    private readonly string _outputDir;

    public SnapshotManager(string? outputDir = null)
    {
        _outputDir = outputDir ?? Directory.GetCurrentDirectory();
        Directory.CreateDirectory(_outputDir);
    }

    public string OutputDir => _outputDir;

    /// <summary>
    /// Save a snapshot BMP with orientation correction.
    /// Portrait frames are rotated 90° CCW so they appear upright when viewed on a PC.
    ///
    /// Returns (snapshotPath, debugImagePath?, rgb565Path?)
    /// </summary>
    public (string snapshot, string? debugImage, string? rgb565) Save(
        Mat frame,
        byte[]? frameBytes = null,
        Orientation orientation = Orientation.Landscape,
        string prefix = "snapshot",
        bool debugMode = false)
    {
        string timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");

        // Rotate portrait frames back to upright for PC viewing
        Mat viewerFrame;
        if (orientation == Orientation.Portrait)
        {
            viewerFrame = new Mat();
            Cv2.Rotate(frame, viewerFrame, RotateFlags.Rotate90Counterclockwise);
        }
        else
        {
            viewerFrame = frame.Clone();
        }

        string snapshotPath = Path.Combine(_outputDir, $"{prefix}_{timestamp}.bmp");
        Cv2.ImWrite(snapshotPath, viewerFrame);
        viewerFrame.Dispose();

        string? debugImagePath = null;
        string? rgb565Path = null;

        if (debugMode)
        {
            debugImagePath = Path.Combine(_outputDir, $"{prefix}_{timestamp}_raw.bmp");
            Cv2.ImWrite(debugImagePath, frame);

            if (frameBytes is not null)
            {
                rgb565Path = Path.Combine(_outputDir, $"{prefix}_{timestamp}_rgb565.bin");
                File.WriteAllBytes(rgb565Path, frameBytes);
            }
        }

        return (snapshotPath, debugImagePath, rgb565Path);
    }

    public string SaveDebugFrame(Mat frame, string filename = "last.bmp")
    {
        string path = Path.Combine(_outputDir, filename);
        Cv2.ImWrite(path, frame);
        return path;
    }
}
