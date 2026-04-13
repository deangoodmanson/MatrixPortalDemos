using LedPortal.Config;

namespace LedPortal.UI;

public static class ConsoleHelp
{
    public static void PrintHelp(
        Orientation orientation,
        ProcessingMode mode,
        bool blackAndWhite,
        bool debugMode,
        double zoomLevel = 1.0,
        bool showPreview = false,
        bool mirror = false,
        string algorithmName = "squares",
        int ledSizePct = 100)
    {
        Console.WriteLine();
        Console.WriteLine(new string('=', 60));
        Console.WriteLine("Commands (single keypress):");
        Console.WriteLine("  Orientation: l=landscape  p=portrait");
        Console.WriteLine("  Processing:  c=center  s=stretch  f=fit");
        Console.WriteLine("  Effects:     b=B&W toggle  m=mirror toggle  z=zoom");
        Console.WriteLine("  Preview:     w=on/off  o=algorithm  +/= size up  -/_ size down (Circles only)");
        Console.WriteLine("  Actions:     SPACE=snapshot");
        Console.WriteLine("  Demo:        x=auto  X=manual  ,/<  ./>  SPACE=pause/resume");
        Console.WriteLine("  System:      t=toggle transmission  d=debug  r=reset  h=help  q=quit");
        Console.WriteLine();

        string bwStr      = blackAndWhite ? "B&W" : "Color";
        string debugStr   = debugMode ? "ON" : "OFF";
        string previewStr = showPreview ? "ON" : "OFF";
        string mirrorStr  = mirror ? "ON" : "OFF";
        int zoomPct       = (int)(zoomLevel * 100);

        Console.WriteLine(
            $"Current: {orientation} + {mode}, {bwStr}, Mirror={mirrorStr}, " +
            $"Debug={debugStr}, Zoom={zoomPct}%, Preview={previewStr}, " +
            $"Algorithm={algorithmName}, Size={ledSizePct}%");
        Console.WriteLine(new string('=', 60));
        Console.WriteLine();
    }

    public static void PrintStatus(string message) =>
        Console.WriteLine($"\n=== {message} ===\n");
}
