namespace LedPortal.Exceptions;

// Base exception for all LED Portal errors
public class LedPortalException(string message, Exception? inner = null)
    : Exception(message, inner);

// Camera exceptions
public class CameraException(string message, Exception? inner = null)
    : LedPortalException(message, inner);

public class CameraNotFoundException(string message)
    : CameraException(message);

public class CameraCaptureFailed(string message, Exception? inner = null)
    : CameraException(message, inner);

// Transport exceptions
public class TransportException(string message, Exception? inner = null)
    : LedPortalException(message, inner);

public class DeviceNotFoundException(string message)
    : TransportException(message);

// Avoid collision with System.Net.Sockets.SocketException
public class SerialConnectionException(string message, Exception? inner = null)
    : TransportException(message, inner);

public class SendException(string message, Exception? inner = null)
    : TransportException(message, inner);

// Config exceptions
public class ConfigException(string message, Exception? inner = null)
    : LedPortalException(message, inner);

public class ConfigNotFoundException(string path)
    : ConfigException($"Configuration file not found: {path}");

public class ConfigValidationException(string message, Exception? inner = null)
    : ConfigException(message, inner);
