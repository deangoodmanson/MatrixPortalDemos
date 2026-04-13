// LED Portal C# — Main entry point
// Top-level statements (C# 9+) eliminate the boilerplate static class Program { static void Main() }.
// CancellationTokenSource + Console.CancelKeyPress replaces Python's KeyboardInterrupt.

using LedPortal.Capture;
using LedPortal.Config;
using LedPortal.Exceptions;
using LedPortal.Processing;
using LedPortal.Transport;
using LedPortal.UI;
using OpenCvSharp;
using System.CommandLine;

// ── CLI argument parsing ────────────────────────────────────────────────────

var configOpt     = new Option<string?>("--config")     { Description = "Path to YAML config file" };
var cameraOpt     = new Option<int?>   ("--camera")     { Description = "Camera index (overrides config)" };
var portOpt       = new Option<string?>("--port")       { Description = "Serial port (overrides auto-detect)" };
var framesOpt     = new Option<int>    ("--frames")     { Description = "Max frames (0=infinite)", DefaultValueFactory = _ => 0 };
var noDisplayOpt  = new Option<bool>   ("--no-display") { Description = "Start with display paused" };
var bwOpt         = new Option<bool>   ("--bw")         { Description = "Start in B&W mode" };
var orientOpt     = new Option<string?>("--orientation") { Description = "landscape or portrait" };
var processingOpt = new Option<string?>("--processing") { Description = "center, stretch, or fit" };

var root = new RootCommand("LED Portal C# — Camera feed for LED matrix display")
{
    configOpt, cameraOpt, portOpt, framesOpt, noDisplayOpt, bwOpt, orientOpt, processingOpt
};

AppConfig? parsedConfig = null;
string? parsedPort = null;
int parsedMaxFrames = 0;
bool parsedNoDisplay = false;
bool parsedBw = false;

root.SetAction(parseResult =>
{
    var configPath = parseResult.GetValue(configOpt);
    try
    {
        parsedConfig = ConfigLoader.Load(configPath);
    }
    catch (ConfigException ex)
    {
        Console.Error.WriteLine($"Configuration error: {ex.Message}");
        Environment.Exit(1);
    }

    if (parseResult.GetValue(cameraOpt) is int camIdx)
        parsedConfig = parsedConfig! with { Camera = parsedConfig.Camera with { Index = camIdx } };

    if (parseResult.GetValue(orientOpt) is string orient)
        parsedConfig = parsedConfig! with
        {
            Processing = parsedConfig.Processing with
            {
                Orientation = orient.Equals("portrait", StringComparison.OrdinalIgnoreCase)
                    ? Orientation.Portrait : Orientation.Landscape
            }
        };

    if (parseResult.GetValue(processingOpt) is string pm)
        parsedConfig = parsedConfig! with
        {
            Processing = parsedConfig.Processing with
            {
                ProcessingMode = pm.ToLower() switch
                {
                    "stretch" => ProcessingMode.Stretch,
                    "fit"     => ProcessingMode.Fit,
                    _         => ProcessingMode.Center,
                }
            }
        };

    parsedPort      = parseResult.GetValue(portOpt);
    parsedMaxFrames = parseResult.GetValue(framesOpt);
    parsedNoDisplay = parseResult.GetValue(noDisplayOpt);
    parsedBw        = parseResult.GetValue(bwOpt);
});

await root.Parse(args).InvokeAsync();

if (parsedConfig is null) return;

// ── Cancellation ────────────────────────────────────────────────────────────
// Note: Ctrl+C is handled by KeyboardHandler (TreatControlCAsInput=true → char 0x03 → Quit)
// rather than CancelKeyPress, which won't fire in that mode.
using var cts = new CancellationTokenSource();

// ── Startup banner ──────────────────────────────────────────────────────────
var config = parsedConfig;
Console.WriteLine("LED Portal C# v1.0.0");
Console.WriteLine($"Matrix: {config.Matrix.Width}×{config.Matrix.Height}");
Console.WriteLine($"Target FPS: {config.TargetFps}");
Console.WriteLine($"Frame size: {config.Matrix.FrameSizeBytes} bytes (RGB565)");
Console.WriteLine();

// ── Mutable runtime state ───────────────────────────────────────────────────
// Config is immutable; key-presses produce new records via `with` expressions.
var orientation      = config.Processing.Orientation;
var processingMode   = config.Processing.ProcessingMode;
bool blackAndWhite   = parsedBw;
bool mirrorMode      = false;
bool debugMode       = config.Ui.DebugMode;
bool displayEnabled  = !parsedNoDisplay;
bool showPreview     = config.Ui.ShowPreview;
double zoomLevel     = 1.0;
var renderAlgorithm  = PreviewAlgorithm.GaussianDiffused;
int ledSizePct       = PreviewWindow.LedSizeDefault;
string demoLabel     = "";
Mat? lastSentFrame   = null;

// ── Device setup ────────────────────────────────────────────────────────────
using var camera = CameraFactory.Create(config.Camera);
try
{
    camera.Open();
    var info = camera.GetCameraInfo();
    Console.WriteLine(new string('=', 60));
    Console.WriteLine("CAMERA:");
    foreach (var (k, v) in info) Console.WriteLine($"  {k}: {v}");
    Console.WriteLine(new string('=', 60));
    Console.WriteLine();
}
catch (CameraNotFoundException ex)
{
    Console.Error.WriteLine($"Camera error: {ex.Message}");
    return;
}

ITransport? transport = null;
try
{
    transport = TransportFactory.Create(config.Transport);
    transport.Connect(parsedPort);
    Console.WriteLine($"Connected to Matrix Portal on {transport.Port}");

    if (displayEnabled)
    {
        var testPattern = TestPatterns.CreateGradientPattern(config.Matrix);
        for (int i = 0; i < 2; i++)
        {
            transport.SendFrame(testPattern);
            Console.WriteLine($"Test pattern {i + 1} sent");
            Thread.Sleep(500);
        }
    }
}
catch (TransportException ex)
{
    Console.WriteLine($"Warning: {ex.Message}");
    Console.WriteLine("Display paused. Press 't' to retry when portal is connected.");
    transport?.Dispose();
    transport = null;
}

var snapshotManager = new SnapshotManager();
var demo = new DemoMode();

ConsoleHelp.PrintHelp(orientation, processingMode, blackAndWhite, debugMode,
    zoomLevel, showPreview, mirrorMode,
    PreviewWindow.AlgorithmLabels[renderAlgorithm], ledSizePct);
Console.WriteLine("Starting — capturing and sending frames...");

// ── Main loop ───────────────────────────────────────────────────────────────
// PeriodicTimer is drift-resistant: it measures from the tick start and corrects
// for jitter. Python's time.sleep() accumulates drift over many iterations.
using var timer = config.Ui.EnableFrameLimiting
    ? new PeriodicTimer(TimeSpan.FromMilliseconds(config.FrameTimeMs))
    : null;

using var keyboard = new KeyboardHandler();
int frameCount = 0;
var startTime = DateTime.UtcNow;

while (!cts.IsCancellationRequested)
{
    if (timer is not null && !await timer.WaitForNextTickAsync(cts.Token).ConfigureAwait(false))
        break;

    // ── Input ───────────────────────────────────────────────────────────────
    var inputResult = keyboard.CheckInput();
    var cmd = inputResult.Command;

    if (demo.IsActive)
    {
        if (cmd == InputCommand.DemoNext)
        {
            var dc = demo.NextStep();
            Console.WriteLine($"\n--- Demo [{demo.StepPosition}]: {dc.Description} ({demo.ControlsHint}) ---");
            cmd = dc.Command; demoLabel = dc.Label;
        }
        else if (cmd == InputCommand.DemoPrev)
        {
            var dc = demo.PrevStep();
            Console.WriteLine($"\n--- Demo [{demo.StepPosition}]: {dc.Description} ({demo.ControlsHint}) ---");
            cmd = dc.Command; demoLabel = dc.Label;
        }
        else if (cmd == InputCommand.Snapshot && demo.State == DemoState.Manual)
        {
            continue;
        }
        else if (cmd == InputCommand.Snapshot && demo.State is DemoState.Auto or DemoState.Paused)
        {
            var newState = demo.TogglePause();
            Console.WriteLine(newState == DemoState.Paused
                ? $"\n=== DEMO: PAUSED [{demo.StepPosition}] ({demo.ControlsHint}) ===\n"
                : "\n=== DEMO: RESUMED ===\n");
            continue;
        }
        else if (cmd == InputCommand.DemoToggle)
        {
            demo.Stop(); demoLabel = "";
            ConsoleHelp.PrintStatus("DEMO MODE: OFF");
            continue;
        }
        else if (cmd == InputCommand.DemoManual)
        {
            continue;
        }
        else if (cmd != InputCommand.None)
        {
            demo.Stop(); demoLabel = "";
            ConsoleHelp.PrintStatus("DEMO MODE: STOPPED");
        }
        else
        {
            var autoDc = demo.GetNextCommand(DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0);
            if (autoDc is not null)
            {
                Console.WriteLine($"\n--- Demo [{demo.StepPosition}]: {autoDc.Description} ({demo.ControlsHint}) ---");
                cmd = autoDc.Command; demoLabel = autoDc.Label;
            }
        }
    }

    // ── Command switch ──────────────────────────────────────────────────────
    bool doCapture = true;
    switch (cmd)
    {
        case InputCommand.OrientationLandscape:
            orientation = Orientation.Landscape; ConsoleHelp.PrintStatus("ORIENTATION: LANDSCAPE"); doCapture = false; break;
        case InputCommand.OrientationPortrait:
            orientation = Orientation.Portrait; ConsoleHelp.PrintStatus("ORIENTATION: PORTRAIT"); doCapture = false; break;
        case InputCommand.ProcessingCenter:
            processingMode = ProcessingMode.Center; ConsoleHelp.PrintStatus("PROCESSING: CENTER CROP"); doCapture = false; break;
        case InputCommand.ProcessingStretch:
            processingMode = ProcessingMode.Stretch; ConsoleHelp.PrintStatus("PROCESSING: STRETCH"); doCapture = false; break;
        case InputCommand.ProcessingFit:
            processingMode = ProcessingMode.Fit; ConsoleHelp.PrintStatus("PROCESSING: FIT"); doCapture = false; break;
        case InputCommand.ToggleBw:
            blackAndWhite = !blackAndWhite; ConsoleHelp.PrintStatus(blackAndWhite ? "BLACK & WHITE MODE" : "COLOR MODE"); doCapture = false; break;
        case InputCommand.ToggleMirror:
            mirrorMode = !mirrorMode; ConsoleHelp.PrintStatus($"MIRROR: {(mirrorMode ? "ON" : "OFF")}"); doCapture = false; break;
        case InputCommand.ZoomToggle:
            zoomLevel = zoomLevel switch { 1.0 => 0.75, 0.75 => 0.5, 0.5 => 0.25, _ => 1.0 };
            ConsoleHelp.PrintStatus($"ZOOM: {(int)(zoomLevel * 100)}%"); doCapture = false; break;
        case InputCommand.CycleRenderAlgorithm:
            renderAlgorithm = (PreviewAlgorithm)(((int)renderAlgorithm + 1) % Enum.GetValues<PreviewAlgorithm>().Length);
            ConsoleHelp.PrintStatus($"RENDER: {PreviewWindow.AlgorithmLabels[renderAlgorithm]}"); doCapture = false; break;
        case InputCommand.LedSizeIncrease:
            if (renderAlgorithm == PreviewAlgorithm.Circles)
            {
                int idx = Array.IndexOf(PreviewWindow.LedSizeSteps, ledSizePct);
                if (idx >= 0 && idx < PreviewWindow.LedSizeSteps.Length - 1)
                    ledSizePct = PreviewWindow.LedSizeSteps[idx + 1];
                ConsoleHelp.PrintStatus($"LED SIZE: {ledSizePct}%");
            }
            doCapture = false; break;
        case InputCommand.LedSizeDecrease:
            if (renderAlgorithm == PreviewAlgorithm.Circles)
            {
                int idx = Array.IndexOf(PreviewWindow.LedSizeSteps, ledSizePct);
                if (idx > 0) ledSizePct = PreviewWindow.LedSizeSteps[idx - 1];
                ConsoleHelp.PrintStatus($"LED SIZE: {ledSizePct}%");
            }
            doCapture = false; break;
        case InputCommand.ToggleDisplay:
            if (transport is null)
            {
                Console.WriteLine("\n=== RECONNECTING ===");
                try
                {
                    transport = TransportFactory.Create(config.Transport);
                    transport.Connect(parsedPort);
                    Console.WriteLine($"Connected on {transport.Port}\n");
                }
                catch (TransportException ex)
                { Console.WriteLine($"Failed: {ex.Message}"); transport?.Dispose(); transport = null; }
            }
            else
            {
                displayEnabled = !displayEnabled;
                ConsoleHelp.PrintStatus(displayEnabled ? "DISPLAY: ENABLED" : "DISPLAY: PAUSED");
            }
            doCapture = false; break;
        case InputCommand.ToggleDebug:
            debugMode = !debugMode; ConsoleHelp.PrintStatus($"DEBUG: {(debugMode ? "ON" : "OFF")}"); doCapture = false; break;
        case InputCommand.TogglePreview:
            showPreview = !showPreview;
            if (!showPreview) PreviewWindow.DestroyAll();
            ConsoleHelp.PrintStatus($"PREVIEW: {(showPreview ? "ENABLED" : "DISABLED")}"); doCapture = false; break;
        case InputCommand.DemoToggle:
            orientation = Orientation.Landscape; processingMode = ProcessingMode.Center;
            blackAndWhite = false; mirrorMode = false; zoomLevel = 1.0;
            demo.StartAuto(); ConsoleHelp.PrintStatus("DEMO MODE: AUTO"); doCapture = false; break;
        case InputCommand.DemoManual:
            orientation = Orientation.Landscape; processingMode = ProcessingMode.Center;
            blackAndWhite = false; mirrorMode = false; zoomLevel = 1.0;
            demo.StartManual();
            { var dc2 = demo.NextStep(); demoLabel = dc2.Label; cmd = dc2.Command; }
            ConsoleHelp.PrintStatus("DEMO MODE: MANUAL"); break;  // fall through to capture
        case InputCommand.Reset:
            orientation = Orientation.Landscape; processingMode = ProcessingMode.Center;
            blackAndWhite = false; mirrorMode = false; debugMode = false; zoomLevel = 1.0;
            renderAlgorithm = PreviewAlgorithm.GaussianDiffused;
            ledSizePct = PreviewWindow.LedSizeDefault; displayEnabled = true;
            ConsoleHelp.PrintStatus("RESET TO DEFAULTS"); doCapture = false; break;
        case InputCommand.Help:
            ConsoleHelp.PrintHelp(orientation, processingMode, blackAndWhite, debugMode,
                zoomLevel, showPreview, mirrorMode,
                PreviewWindow.AlgorithmLabels[renderAlgorithm], ledSizePct);
            doCapture = false; break;
        case InputCommand.Quit:
            cts.Cancel(); doCapture = false; break;
        case InputCommand.Snapshot:
            RunSnapshotSequence(camera, transport, config, snapshotManager, keyboard,
                orientation, processingMode, blackAndWhite, mirrorMode,
                zoomLevel, debugMode, renderAlgorithm, ledSizePct, showPreview);
            keyboard.ClearBuffer(); doCapture = false; break;
    }

    if (!doCapture) continue;

    // ── Frame pipeline ──────────────────────────────────────────────────────
    Mat originalFrame;
    try { originalFrame = camera.Capture(); }
    catch (CameraCaptureFailed) { Thread.Sleep(100); continue; }

    using (originalFrame)
    {
        using var workingFrame = ZoomCropper.ApplyZoomCrop(originalFrame, zoomLevel);
        var updatedProcessing = config.Processing with { Orientation = orientation, ProcessingMode = processingMode };
        using var smallFrame = FrameResizer.ResizeFrame(workingFrame, config.Matrix, updatedProcessing);

        Mat effectFrame = smallFrame;
        Mat? mirrorResult = null, bwResult = null;
        if (mirrorMode)    { mirrorResult = ColorProcessor.ApplyMirror(effectFrame, orientation);  effectFrame = mirrorResult; }
        if (blackAndWhite) { bwResult     = ColorProcessor.ApplyGrayscale(effectFrame);             effectFrame = bwResult; }

        using var previewFrame = effectFrame.Clone();

        if (demo.IsActive && !string.IsNullOrEmpty(demoLabel))
        {
            var labeled = PreviewWindow.DrawTextOverlay(effectFrame, demoLabel, new Point(2, 30),
                new Scalar(0, 0, 255), 0.225, 1);
            if (effectFrame != smallFrame && effectFrame != mirrorResult && effectFrame != bwResult)
                effectFrame.Dispose();
            effectFrame = labeled;
        }

        Mat limitedFrame = effectFrame;
        Mat? limitResult = null;
        if (config.Processing.MaxBrightness < 255)
        {
            limitResult = ColorProcessor.ApplyBrightnessLimit(effectFrame, config.Processing.MaxBrightness);
            limitedFrame = limitResult;
        }

        if (config.DebugSaveFrames) snapshotManager.SaveDebugFrame(limitedFrame);

        var frameBytes = ColorProcessor.ConvertToRgb565(limitedFrame);

        if (displayEnabled && transport is not null)
        {
            try
            {
                transport.SendFrame(frameBytes);
                lastSentFrame?.Dispose();
                lastSentFrame = limitedFrame.Clone();
                frameCount++;
                if (frameCount == 1) Console.WriteLine($"First frame sent: {frameBytes.Length} bytes");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Display disconnected: {ex.Message}");
                transport.Dispose(); transport = null;
            }
        }
        else { frameCount++; }

        if (debugMode && frameCount % 10 == 0 && frameCount > 0)
        {
            double elapsed = (DateTime.UtcNow - startTime).TotalSeconds;
            Console.WriteLine($"Frames: {frameCount}, FPS: {frameCount / elapsed:F1}, " +
                $"Orient: {orientation}, Mode: {processingMode}, Zoom: {(int)(zoomLevel * 100)}%");
        }

        if (showPreview)
        {
            PreviewWindow.Show(originalFrame, previewFrame, config.Matrix,
                orientation, processingMode, zoomLevel, renderAlgorithm, ledSizePct,
                config.Processing.MaxBrightness, demo.IsActive ? demoLabel : "");
        }

        mirrorResult?.Dispose();
        bwResult?.Dispose();
        limitResult?.Dispose();
    }

    if (parsedMaxFrames > 0 && frameCount >= parsedMaxFrames)
    {
        Console.WriteLine($"Reached {parsedMaxFrames} frames. Stopping.");
        break;
    }
}

// ── Cleanup ──────────────────────────────────────────────────────────────────
lastSentFrame?.Dispose();
transport?.Dispose();
if (showPreview) PreviewWindow.DestroyAll();
Console.WriteLine("LED Portal stopped.");

// ── Snapshot sequence helper ──────────────────────────────────────────────────
static void RunSnapshotSequence(
    ICamera camera, ITransport? transport, AppConfig config,
    SnapshotManager snapshotManager, KeyboardHandler keyboard,
    Orientation orientation, ProcessingMode processingMode,
    bool blackAndWhite, bool mirror, double zoomLevel, bool debugMode,
    PreviewAlgorithm renderAlgorithm, int ledSizePct, bool showPreview)
{
    Console.WriteLine("\n=== SNAPSHOT MODE (press any key to cancel) ===");
    Console.WriteLine($"Countdown: 3... 2... 1... ({config.Ui.CountdownDuration}s each)");

    Mat? lastSmallFrame = null;
    var updatedProcessing = config.Processing with { Orientation = orientation, ProcessingMode = processingMode };

    foreach (int countdown in new[] { 3, 2, 1 })
    {
        Console.Write($"  {countdown}... "); Console.Out.Flush();
        var countdownStart = DateTime.UtcNow;

        while ((DateTime.UtcNow - countdownStart).TotalSeconds < config.Ui.CountdownDuration)
        {
            if (keyboard.CheckAbort())
            {
                Console.WriteLine("\n=== SNAPSHOT CANCELLED ===\n");
                keyboard.ClearBuffer();
                lastSmallFrame?.Dispose();
                return;
            }

            Mat frame;
            try { frame = camera.Capture(); } catch { Thread.Sleep(10); continue; }

            using (frame)
            {
                using var zoomed = ZoomCropper.ApplyZoomCrop(frame, zoomLevel);
                var small = FrameResizer.ResizeFrame(zoomed, config.Matrix, updatedProcessing);
                if (mirror)         { var m  = ColorProcessor.ApplyMirror(small, orientation); small.Dispose(); small = m; }
                if (blackAndWhite)  { var bw = ColorProcessor.ApplyGrayscale(small); small.Dispose(); small = bw; }

                if (countdown == 1) { lastSmallFrame?.Dispose(); lastSmallFrame = small.Clone(); }

                using var bordered = PreviewWindow.DrawBorder(small, countdown == 1 ? Scalar.Blue : null);
                using var overlay  = PreviewWindow.DrawCountdownOverlay(bordered, countdown, config.Matrix, orientation);
                var bytes = ColorProcessor.ConvertToRgb565(overlay);
                try { transport?.SendFrame(bytes); } catch { }
                small.Dispose();
            }
            Thread.Sleep(10);
        }
    }

    if (lastSmallFrame is null) return;

    Console.WriteLine("SNAP!");
    var frameBytes = ColorProcessor.ConvertToRgb565(lastSmallFrame);
    var (path, debugPath, _) = snapshotManager.Save(lastSmallFrame, frameBytes, orientation, debugMode: debugMode);

    Console.WriteLine(new string('=', 60));
    Console.WriteLine($"SNAPSHOT SAVED: {path}");
    if (debugMode && debugPath is not null) Console.WriteLine($"  Debug: {debugPath}");
    Console.WriteLine(new string('=', 60));

    using var b2 = PreviewWindow.DrawBorder(lastSmallFrame, Scalar.Blue);
    try { transport?.SendFrame(ColorProcessor.ConvertToRgb565(b2)); } catch { }
    lastSmallFrame.Dispose();

    int pause = (int)config.Ui.SnapshotPauseDuration;
    Console.Write("Resuming in: ");
    for (int i = pause; i > 0; i--)
    {
        if (keyboard.CheckAbort()) { Console.WriteLine(" Now!\n"); keyboard.ClearBuffer(); return; }
        Console.Write($"{i}... "); Console.Out.Flush();
        Thread.Sleep(1000);
    }
    Console.WriteLine("GO!\n");
}
