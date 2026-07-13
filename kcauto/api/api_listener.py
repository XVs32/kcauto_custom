from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import queue
import threading
from typing import Callable, Optional, Dict, Any

from util.logger import Log


class PoiWebhookServer:
    def __init__(self, port=9223):
        self.port = port
        self.api_queue: queue.Queue = queue.Queue()
        # Default filter: allow all APIs starting with '/kcsapi/'
        self.filter_func: Callable[[str, Dict[str, Any]], bool] = lambda path, data: (
            path.startswith("/kcsapi/")
        )
        self.server: Optional[HTTPServer] = None
        self.server_thread: Optional[threading.Thread] = None

    def set_port(self, port: int):
        self.port = port

    def set_filter(self, filter_function: Callable[[str, Dict[str, Any]], bool]):
        """
        Set a custom filter function to determine which APIs can enter the queue.
        The filter_function must accept (api_path, full_data) and return a Boolean.
        """
        self.filter_func = filter_function
        Log.log_debug_1(f"Custom filter has been applied.")

    def pop_msg(
        self, block: bool = False, timeout: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve the oldest API data from the queue (FIFO).
        - block=False: Returns None immediately if the queue is empty.
        - block=True: Blocks until an item is available or timeout occurs.
        """
        try:
            return self.api_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def _start_http_server(self):
        # Use closure to pass reference of queue and filter to the HTTP Handler
        outer_self = self

        class WebhookHandler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path == "/webhook/kancolle":
                    content_length = int(self.headers["Content-Length"])
                    post_data = self.rfile.read(content_length)

                    try:
                        data = json.loads(post_data.decode("utf-8"))
                        api_path = data.get("path", "")

                        # Check if the API matches developer's filter condition
                        if outer_self.filter_func(api_path, data):
                            outer_self.api_queue.put(data)
                            status = "ACCEPTED & QUEUED"
                        else:
                            status = "FILTERED OUT"

                        # Respond to poi browser
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": status}).encode("utf-8"))

                    except Exception as e:
                        self.send_response(500)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

            # Override to disable default HTTP logging and keep console clean
            def log_message(self, format, *args):
                pass

        self.server = HTTPServer(("", self.port), WebhookHandler)
        Log.log_success(f"Webhook server started, listening on Port {self.port}...")
        self.server.serve_forever()

    def start(self):
        """Start the HTTP server in a background daemon thread to avoid blocking the main thread"""
        self.server_thread = threading.Thread(
            target=self._start_http_server, daemon=True
        )
        self.server_thread.start()


api_listener = PoiWebhookServer()
