namespace LedPortal.UI;

public enum InputCommand
{
    None,
    // Orientation
    OrientationLandscape,
    OrientationPortrait,
    // Processing
    ProcessingCenter,
    ProcessingStretch,
    ProcessingFit,
    // Effects
    ToggleBw,
    ToggleMirror,
    ZoomToggle,
    CycleRenderAlgorithm,
    LedSizeIncrease,
    LedSizeDecrease,
    // Actions
    Snapshot,
    ToggleDisplay,
    ToggleDebug,
    TogglePreview,
    // Demo
    DemoToggle,
    DemoManual,
    DemoNext,
    DemoPrev,
    // System
    Reset,
    Help,
    Quit,
    Abort,
}

/// <summary>
/// Result of a keyboard check.
/// readonly record struct = zero-allocation value type (no heap pressure per frame).
/// </summary>
public readonly record struct InputResult(InputCommand Command, char? RawInput = null);

/// <summary>
/// Non-blocking keyboard handler using a background reader thread.
///
/// Problem: Console.KeyAvailable returns false until Enter is pressed (cooked/line-buffered
/// mode). Console.ReadKey() is what switches Unix terminals to raw mode — but if we only
/// call ReadKey when KeyAvailable is true, we deadlock: raw mode is never set, so
/// KeyAvailable never fires.
///
/// Fix: a background thread that always blocks on Console.ReadKey(intercept:true). The
/// first call sets raw mode so keys arrive immediately without Enter. Keys are fed into a
/// ConcurrentQueue; the main loop dequeues non-blocking.
///
/// Ctrl+C: with TreatControlCAsInput=true, Ctrl+C arrives as char(0x03) instead of
/// raising SIGINT. We map it to Quit so the main loop can exit cleanly.
/// </summary>
public sealed class KeyboardHandler : IDisposable
{
    private static readonly Dictionary<char, InputCommand> KeyMap = new()
    {
        ['l'] = InputCommand.OrientationLandscape,
        ['p'] = InputCommand.OrientationPortrait,
        ['c'] = InputCommand.ProcessingCenter,
        ['s'] = InputCommand.ProcessingStretch,
        ['f'] = InputCommand.ProcessingFit,
        ['b'] = InputCommand.ToggleBw,
        ['m'] = InputCommand.ToggleMirror,
        ['z'] = InputCommand.ZoomToggle,
        ['o'] = InputCommand.CycleRenderAlgorithm,
        ['+'] = InputCommand.LedSizeIncrease,
        ['='] = InputCommand.LedSizeIncrease,
        ['-'] = InputCommand.LedSizeDecrease,
        ['_'] = InputCommand.LedSizeDecrease,
        [' '] = InputCommand.Snapshot,
        ['x'] = InputCommand.DemoToggle,
        ['X'] = InputCommand.DemoManual,
        ['.'] = InputCommand.DemoNext,
        ['>'] = InputCommand.DemoNext,
        [','] = InputCommand.DemoPrev,
        ['<'] = InputCommand.DemoPrev,
        ['t'] = InputCommand.ToggleDisplay,
        ['d'] = InputCommand.ToggleDebug,
        ['w'] = InputCommand.TogglePreview,
        ['r'] = InputCommand.Reset,
        ['h'] = InputCommand.Help,
        ['q'] = InputCommand.Quit,
    };

    private readonly System.Collections.Concurrent.ConcurrentQueue<ConsoleKeyInfo> _keyQueue = new();
    private readonly Thread _readerThread;
    private volatile bool _disposed;

    public KeyboardHandler()
    {
        // Intercept Ctrl+C as input (char 0x03) instead of raising SIGINT.
        // This lets us return Quit from CheckInput() for a clean shutdown.
        Console.TreatControlCAsInput = true;

        _readerThread = new Thread(ReadLoop) { IsBackground = true, Name = "KeyboardReader" };
        _readerThread.Start();
    }

    private void ReadLoop()
    {
        // First ReadKey call switches the Unix terminal from cooked to raw mode.
        // Subsequent KeyAvailable checks (if any) then see individual keystrokes.
        while (!_disposed)
        {
            try
            {
                var key = Console.ReadKey(intercept: true);
                _keyQueue.Enqueue(key);
            }
            catch (InvalidOperationException) { break; }  // stdin redirected / not a tty
        }
    }

    /// <summary>Non-blocking check. Returns None if no key is queued.</summary>
    public InputResult CheckInput()
    {
        if (!_keyQueue.TryDequeue(out var keyInfo))
            return new InputResult(InputCommand.None);

        char c = keyInfo.KeyChar;

        // Ctrl+C (char 0x03) → clean quit
        if (c == '\x03')
            return new InputResult(InputCommand.Quit, c);

        // X (Shift+x) is case-sensitive — check before lowercasing
        if (KeyMap.TryGetValue(c, out var cmd))
            return new InputResult(cmd, c);

        // Lowercase fallback for shift variants of letter keys
        if (KeyMap.TryGetValue(char.ToLower(c), out cmd))
            return new InputResult(cmd, c);

        return new InputResult(InputCommand.None, c);
    }

    public bool CheckAbort() => CheckInput().Command == InputCommand.Snapshot;

    /// <summary>Drain any queued keystrokes (e.g., after snapshot).</summary>
    public void ClearBuffer()
    {
        while (_keyQueue.TryDequeue(out _)) { }
    }

    public void Dispose()
    {
        _disposed = true;
        // Restore Ctrl+C to default signal behaviour for clean shell handoff
        try { Console.TreatControlCAsInput = false; } catch { }
        // Background thread is daemon — it dies with the process; no join needed
    }
}
