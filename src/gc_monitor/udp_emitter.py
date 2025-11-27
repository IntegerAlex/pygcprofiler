"""UDP emitter for live monitoring."""


class UdpEmitter:
    """
    Fire-and-forget UDP emitter for live monitoring.
    Designed to never block or crash the application.
    """
    __slots__ = ('sock', 'address', 'enabled')

    def __init__(self, host='127.0.0.1', port=8989):
        self.address = (host, port)
        self.enabled = True
        try:
            import socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setblocking(False)
        except Exception:
            # If we can't create a socket, just disable live monitoring
            self.enabled = False

    def emit(self, event_data):
        if not self.enabled:
            return

        try:
            import json
            # Minimal JSON serialization
            payload = json.dumps(event_data).encode('utf-8')
            self.sock.sendto(payload, self.address)
        except Exception:
            # Ignore ALL errors (network down, buffer full, serialization fail)
            # We never want to crash the app for a visualization feature
            pass

