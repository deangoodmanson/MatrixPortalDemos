using LedPortal.Config;

namespace LedPortal.Transport;

public static class TransportFactory
{
    public static ITransport Create(TransportConfig config) => new SerialTransport(config);
}
