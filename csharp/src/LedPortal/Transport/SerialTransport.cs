using System.IO.Ports;
using System.Text;
using LedPortal.Config;
using LedPortal.Exceptions;

namespace LedPortal.Transport;

/// <summary>
/// USB CDC serial transport for the Adafruit Matrix Portal M4/S3.
///
/// Protocol: ASCII "IMG1" header (4 bytes) + RGB565 frame data (4096 bytes).
/// Baud rate: 4,000,000 bps.
///
/// Key .NET note: SerialPort.BaseStream.Write(ReadOnlySpan&lt;byte&gt;) accepts a span
/// directly on .NET 9+, avoiding a ToArray() copy. This replaces Python's
/// serial.Serial.write(bytes).
/// </summary>
public sealed class SerialTransport : ITransport
{
    private readonly TransportConfig _config;
    private SerialPort? _port;
    private string? _portName;

    public SerialTransport(TransportConfig config) => _config = config;

    public bool IsConnected => _port?.IsOpen ?? false;
    public string? Port => _portName;
    public string TransportType => "serial";

    public void Connect(string? port = null)
    {
        port ??= FindMatrixPortalPort()
            ?? throw new DeviceNotFoundException(
                $"Matrix Portal not found. Available ports: [{string.Join(", ", GetPortNames())}]");

        try
        {
            _port = new SerialPort(port, _config.BaudRate)
            {
                ReadTimeout = (int)(_config.Timeout * 1000),
                WriteTimeout = (int)(_config.WriteTimeout * 1000),
                // Prevent DTR reset on CircuitPython — must be set after construction
                DtrEnable = false,
                RtsEnable = false,
            };

            _port.Open();

            // Wait for CircuitPython to boot (~1.5–2s if it reset on open)
            Console.WriteLine("Waiting for Matrix Portal to be ready...");
            Thread.Sleep(2000);

            _port.DiscardInBuffer();
            _port.DiscardOutBuffer();
            _portName = port;
        }
        catch (Exception ex) when (ex is not TransportException)
        {
            throw new SerialConnectionException($"Failed to connect to {port}: {ex.Message}", ex);
        }
    }

    public void Disconnect()
    {
        if (_port?.IsOpen == true)
        {
            try { _port.Close(); } catch { /* best-effort */ }
        }
        _port?.Dispose();
        _port = null;
        _portName = null;
    }

    public int SendFrame(ReadOnlySpan<byte> frameData)
    {
        if (_port is not { IsOpen: true })
            throw new SendException("Serial port is not open");

        try
        {
            // Write header
            var headerBytes = Encoding.ASCII.GetBytes(_config.FrameHeader);
            _port.BaseStream.Write(headerBytes);

            // Write frame data — BaseStream.Write accepts ReadOnlySpan<byte> on .NET 9+
            _port.BaseStream.Write(frameData);
            _port.BaseStream.Flush();

            // 10ms margin lets CircuitPython process the frame before the next one arrives.
            // At 4M baud, 4100 bytes takes ~8ms; this adds 2ms processing headroom.
            Thread.Sleep(10);

            return frameData.Length;
        }
        catch (Exception ex) when (ex is not TransportException)
        {
            throw new SendException($"Failed to send frame: {ex.Message}", ex);
        }
    }

    /// <summary>Scan serial ports for a Matrix Portal device.</summary>
    public static string? FindMatrixPortalPort()
    {
        var candidates = new List<string>();

        foreach (var portName in SerialPort.GetPortNames())
        {
            // On macOS, Matrix Portal appears as /dev/cu.usbmodem* or /dev/tty.usbmodem*
            // We can't easily read the USB descriptor without platform APIs, so match by name pattern
            if (portName.Contains("usbmodem", StringComparison.OrdinalIgnoreCase) ||
                portName.Contains("CircuitPython", StringComparison.OrdinalIgnoreCase) ||
                portName.Contains("Matrix", StringComparison.OrdinalIgnoreCase))
            {
                candidates.Add(portName);
            }
        }

        if (candidates.Count == 0)
            return null;

        // If multiple, prefer the higher-numbered port (typically the data port, not REPL)
        candidates.Sort(StringComparer.OrdinalIgnoreCase);
        return candidates[^1];  // ^1 = last element — C# index from end
    }

    private static IEnumerable<string> GetPortNames() =>
        SerialPort.GetPortNames().DefaultIfEmpty("(none)");

    public void Dispose() => Disconnect();
}
