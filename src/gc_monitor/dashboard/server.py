import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional

try:
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, StreamingResponse
    import uvicorn
except ImportError:
    print("Error: Dashboard requires 'fastapi' and 'uvicorn'.")
    print("Install them with: pip install fastapi uvicorn")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gc-dashboard")

app = FastAPI(title="GC Monitor Dashboard")

# Store connected SSE clients (queues for each connection)
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[asyncio.Queue] = []

    def add_connection(self, queue: asyncio.Queue):
        self.active_connections.append(queue)
        logger.debug(f"New SSE connection, total: {len(self.active_connections)}")

    def remove_connection(self, queue: asyncio.Queue):
        if queue in self.active_connections:
            self.active_connections.remove(queue)
        logger.debug(f"SSE connection removed, total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        if not self.active_connections:
            logger.debug("No active SSE connections to broadcast to")
            return
        
        logger.info(f"Broadcasting to {len(self.active_connections)} SSE connection(s)")
        message_json = json.dumps(message)
        # Remove disconnected queues
        disconnected = []
        for queue in self.active_connections.copy():  # Use copy to avoid modification during iteration
            try:
                # Use put_nowait - queue is unbounded so this should never block
                queue.put_nowait(message_json)
                logger.debug(f"Queued message for SSE client")
            except Exception as e:
                logger.warning(f"Error sending to SSE queue: {e}")
                disconnected.append(queue)
        
        # Clean up disconnected queues
        for queue in disconnected:
            self.remove_connection(queue)

manager = ConnectionManager()

# UDP Listener Protocol
class UDPListener(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport
        logger.info("UDP Listener started")

    def datagram_received(self, data, addr):
        try:
            message = json.loads(data.decode())
            logger.info(f"Received UDP packet from {addr}")
            # Broadcast immediately to all connected SSE clients
            # Get the event loop and create task
            loop = asyncio.get_event_loop()
            loop.create_task(manager.broadcast(message))
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding UDP packet from {addr}: {e}, data: {data[:100]}")
        except Exception as e:
            logger.error(f"Error processing UDP packet from {addr}: {e}", exc_info=True)

    def error_received(self, exc):
        logger.error(f"UDP listener error: {exc}")

@app.get("/events")
async def events_stream():
    """Server-Sent Events endpoint for real-time GC event streaming."""
    async def event_generator():
        # Create a queue for this connection (unbounded queue)
        queue = asyncio.Queue()
        manager.add_connection(queue)
        
        try:
            # Send initial connection message
            logger.info("SSE client connected")
            yield f"data: {json.dumps({'type': 'connected'})}\n\n"
            
            # Keep connection alive and send events
            while True:
                try:
                    # Wait for message with timeout to keep connection alive
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)
                    logger.info(f"Sending SSE message: {message[:100]}")
                    # Ensure proper SSE format with double newline
                    yield f"data: {message}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive ping (comment line, no data)
                    yield ": keepalive\n\n"
                except asyncio.CancelledError:
                    logger.info("SSE connection cancelled by client")
                    break
        except GeneratorExit:
            logger.info("SSE generator exited")
        except Exception as e:
            logger.error(f"SSE connection error: {e}", exc_info=True)
        finally:
            logger.info("SSE client disconnected")
            manager.remove_connection(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )

# Serve static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def get():
    index_file = static_dir / "index.html"
    if not index_file.exists():
        logger.error(f"index.html not found at {index_file}")
        return HTMLResponse(content="<h1>Error: Dashboard HTML not found</h1>", status_code=500)
    try:
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Error reading index.html: {e}")
        return HTMLResponse(content="<h1>Error loading dashboard</h1>", status_code=500)

# Store UDP transport for cleanup
_udp_transport: Optional[asyncio.DatagramTransport] = None

def start_server(host="127.0.0.1", http_port=8000, udp_port=8989):
    """Start the GC Monitor Dashboard server.
    
    Args:
        host: Host address to bind to (default: 127.0.0.1)
        http_port: HTTP port for the web interface (default: 8000)
        udp_port: UDP port for receiving GC events (default: 8989)
    """
    global _udp_transport
    
    # We need to run the UDP listener and the Uvicorn server in the same loop.
    # Uvicorn takes control of the loop, so we use a startup event in FastAPI
    # to start the UDP listener.
    
    @app.on_event("startup")
    async def startup_event():
        global _udp_transport
        try:
            logger.info(f"Starting UDP listener on {host}:{udp_port}")
            _udp_transport, protocol = await asyncio.get_running_loop().create_datagram_endpoint(
                lambda: UDPListener(),
                local_addr=(host, udp_port)
            )
            logger.info("UDP listener started successfully")
        except OSError as e:
            logger.error(f"Failed to start UDP listener on {host}:{udp_port}: {e}")
            raise
    
    @app.on_event("shutdown")
    async def shutdown_event():
        global _udp_transport
        if _udp_transport:
            _udp_transport.close()
            logger.info("UDP listener closed")
    
    print(f"Starting Dashboard on http://{host}:{http_port}")
    print(f"Listening for GC events on UDP {host}:{udp_port}")
    
    uvicorn.run(app, host=host, port=http_port, log_level="warning")

if __name__ == "__main__":
    start_server()
