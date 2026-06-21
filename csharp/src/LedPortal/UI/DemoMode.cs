using LedPortal.UI;

namespace LedPortal.UI;

public enum DemoState { Off, Auto, Paused, Manual }

public record DemoStep(InputCommand Command, string Description, double Duration, string Label);
public record DemoCommand(InputCommand Command, string Description, string Label);

public class DemoMode
{
    private readonly double _stepDuration;
    private readonly List<DemoStep> _sequence;
    private DemoState _state = DemoState.Off;
    private int _stepIndex = 0;
    private double _stepStartTime = 0.0;

    public DemoMode(double stepDuration = 3.0)
    {
        _stepDuration = stepDuration;
        _sequence = BuildSequence(stepDuration);
    }

    public DemoState State => _state;
    public bool IsActive => _state != DemoState.Off;
    public string StepPosition => $"{_stepIndex + 1}/{_sequence.Count}";

    public string ControlsHint => _state switch
    {
        DemoState.Auto    => "SPACE=pause, ./>=next, ,/<=prev, x=stop",
        DemoState.Paused  => "SPACE=resume, ./>=next, ,/<=prev, x=stop",
        DemoState.Manual  => "./>=next, ,/<=prev, x=stop",
        _                 => "",
    };

    public void StartAuto()  { _state = DemoState.Auto;   _stepIndex = 0; _stepStartTime = 0.0; }
    public void StartManual(){ _state = DemoState.Manual; _stepIndex = 0; _stepStartTime = 0.0; }
    public void Stop()       { _state = DemoState.Off; }

    public void Pause()
    {
        if (_state == DemoState.Auto) _state = DemoState.Paused;
    }

    public void Resume()
    {
        if (_state == DemoState.Paused) { _state = DemoState.Auto; _stepStartTime = 0.0; }
    }

    public DemoState TogglePause()
    {
        if (_state == DemoState.Auto) Pause();
        else if (_state == DemoState.Paused) Resume();
        return _state;
    }

    public DemoCommand NextStep()
    {
        var step = _sequence[_stepIndex];
        var fired = new DemoCommand(step.Command, step.Description, step.Label);
        _stepIndex = (_stepIndex + 1) % _sequence.Count;
        _stepStartTime = GetTime();
        return fired;
    }

    public DemoCommand PrevStep()
    {
        _stepIndex = ((_stepIndex - 2) % _sequence.Count + _sequence.Count) % _sequence.Count;
        var step = _sequence[_stepIndex];
        var fired = new DemoCommand(step.Command, step.Description, step.Label);
        _stepIndex = (_stepIndex + 1) % _sequence.Count;
        _stepStartTime = GetTime();
        return fired;
    }

    /// <summary>
    /// In AUTO mode: check whether current step's duration has elapsed.
    /// Returns the command to inject, or null if nothing to do yet.
    /// </summary>
    public DemoCommand? GetNextCommand(double currentTime)
    {
        if (_state != DemoState.Auto) return null;

        var step = _sequence[_stepIndex];

        // _stepStartTime == 0 signals "fire immediately on first tick"
        if (_stepStartTime != 0.0 && currentTime - _stepStartTime < step.Duration)
            return null;

        var fired = new DemoCommand(step.Command, step.Description, step.Label);
        _stepIndex = (_stepIndex + 1) % _sequence.Count;
        _stepStartTime = currentTime;
        return fired;
    }

    private static double GetTime() => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0;

    // ── Sequence construction ──────────────────────────────────────────────

    private static List<DemoStep> BuildSequence(double d)
    {
        var steps = new List<DemoStep>();

        // Landscape pass: preview algorithms + effects
        steps.Add(new(InputCommand.OrientationLandscape, "Landscape orientation", d, "Landscape"));
        steps.AddRange(PreviewSteps(d));
        steps.AddRange(EffectsSteps(d));

        // Portrait pass: effects only
        steps.Add(new(InputCommand.OrientationPortrait, "Portrait orientation", d, "Portrait"));
        steps.AddRange(EffectsSteps(d));

        return steps;
    }

    private static IEnumerable<DemoStep> EffectsSteps(double d) =>
    [
        new(InputCommand.ProcessingStretch, "Stretch processing", d, "Stretch"),
        new(InputCommand.ProcessingFit,     "Fit processing",     d, "Fit"),
        new(InputCommand.ProcessingCenter,  "Center processing (restore)", d, "Center"),
        new(InputCommand.ToggleBw,          "B&W on",             d, "B&W"),
        new(InputCommand.ToggleBw,          "B&W off (restore)",  d, "Color"),
        new(InputCommand.ToggleMirror,      "Mirror on",          d, "Mirror"),
        new(InputCommand.ToggleMirror,      "Mirror off (restore)", d, "No Mirror"),
        new(InputCommand.ZoomToggle,        "Zoom 75%",  d, "Zoom 75%"),
        new(InputCommand.ZoomToggle,        "Zoom 50%",  d, "Zoom 50%"),
        new(InputCommand.ZoomToggle,        "Zoom 25%",  d, "Zoom 25%"),
        new(InputCommand.ZoomToggle,        "Zoom 100% (restore)", d, "Zoom 100%"),
    ];

    private static IEnumerable<DemoStep> PreviewSteps(double d) =>
    [
        new(InputCommand.CycleRenderAlgorithm, "Squares",             d, "Squares"),
        new(InputCommand.CycleRenderAlgorithm, "Circles Size=100%",   d, "Circle 100%"),
        new(InputCommand.LedSizeIncrease,      "Circles Size=125%",   d, "Circle 125%"),
        new(InputCommand.LedSizeIncrease,      "Circles Size=150%",   d, "Circle 150%"),
        new(InputCommand.LedSizeDecrease,      "Circles Size=125%",   d, "Circle 125%"),
        new(InputCommand.LedSizeDecrease,      "Circles Size=100%",   d, "Circle 100%"),
        new(InputCommand.LedSizeDecrease,      "Circles Size=75%",    d, "Circle 75%"),
        new(InputCommand.LedSizeDecrease,      "Circles Size=50%",    d, "Circle 50%"),
        new(InputCommand.LedSizeDecrease,      "Circles Size=25%",    d, "Circle 25%"),
        // Restore to 100% (0-duration steps — fire immediately)
        new(InputCommand.LedSizeIncrease, "Circles Size=50%",    0.0, ""),
        new(InputCommand.LedSizeIncrease, "Circles Size=75%",    0.0, ""),
        new(InputCommand.LedSizeIncrease, "Circles Size=100%",   0.0, ""),
        new(InputCommand.CycleRenderAlgorithm, "Raw panel emulation",              d, "Gaussian Raw"),
        new(InputCommand.CycleRenderAlgorithm, "Diffused panel emulation (restore)", d, "Gaussian Diff"),
    ];
}
