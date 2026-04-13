namespace LedPortal.Transport;

/// <summary>
/// Transport abstraction for sending frames to the LED matrix.
/// ReadOnlySpan&lt;byte&gt; replaces Python's `bytes` — it is a zero-copy,
/// stack-only view over any contiguous memory that prevents accidental mutation.
/// </summary>
public interface ITransport : IDisposable
{
    bool IsConnected { get; }
    string? Port { get; }
    string TransportType { get; }

    void Connect(string? port = null);
    void Disconnect();

    /// <summary>Send a frame. Returns number of data bytes sent (excluding header).</summary>
    int SendFrame(ReadOnlySpan<byte> frameData);
}
