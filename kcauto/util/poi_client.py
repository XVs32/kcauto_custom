import json
import socket
import struct
import threading
from typing import Any, Optional

from PIL import Image


class PoiClientError(RuntimeError):
    """Raised when the POI interaction service cannot fulfill a request."""


class PoiClient:
    """Synchronous client for the POI API Forwarder interaction service.

    Packets use a four-byte little-endian payload length followed by a one-byte
    payload type. JSON packets carry commands and acknowledgements. Frame
    packets carry a request id, dimensions, channel count, and raw BGRA data.
    """

    JSON_PACKET = 1
    FRAME_PACKET = 2
    MAX_PACKET_SIZE = 64 * 1024 * 1024
    DEFAULT_TIMEOUT = 10

    def __init__(self, host="127.0.0.1", port=38591):
        self.host = host
        self.port = port
        self._socket: Optional[socket.socket] = None
        self._receiver: Optional[threading.Thread] = None
        self._condition = threading.Condition()
        self._send_lock = threading.Lock()
        self._responses: dict[int, dict[str, Any]] = {}
        self._frames: dict[int, tuple[int, int, int, bytes]] = {}
        self._next_request_id = 1
        self._receiver_error: Optional[BaseException] = None

    @property
    def connected(self):
        return self._socket is not None and self._receiver_error is None

    def connect(self, timeout=DEFAULT_TIMEOUT):
        self.close()
        sock = socket.create_connection((self.host, self.port), timeout=timeout)
        sock.settimeout(None)
        self._socket = sock
        self._receiver_error = None
        self._receiver = threading.Thread(
            target=self._receive_loop,
            args=(sock,),
            daemon=True,
        )
        self._receiver.start()

        response = self._request_json("hello", timeout=timeout, protocol=1)
        if response.get("protocol") != 1:
            self.close()
            raise PoiClientError("Unsupported POI interaction protocol")
        return response

    def close(self):
        sock = self._socket
        receiver = self._receiver
        self._socket = None
        self._receiver = None
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            sock.close()

        with self._condition:
            self._responses.clear()
            self._frames.clear()
            self._condition.notify_all()

        if receiver is not None and receiver is not threading.current_thread():
            receiver.join(timeout=1)

    def health_check(self, timeout=3):
        response = self._request_json("ping", timeout=timeout)
        return response.get("type") == "pong"

    def capture(self, timeout=DEFAULT_TIMEOUT):
        request_id = self._send_request("capture")
        width, height, channels, bitmap = self._wait_for_frame(request_id, timeout)
        if channels != 4 or len(bitmap) != width * height * channels:
            raise PoiClientError("POI returned an invalid BGRA frame")
        return Image.frombytes("RGBA", (width, height), bitmap, "raw", "BGRA").convert(
            "RGB"
        )

    def click(self, x, y, timeout=DEFAULT_TIMEOUT):
        self._request_json("click", timeout=timeout, x=int(x), y=int(y))

    def hover(self, x, y, timeout=DEFAULT_TIMEOUT):
        self._request_json("hover", timeout=timeout, x=int(x), y=int(y))

    def scroll(self, x, y, delta_y, timeout=DEFAULT_TIMEOUT):
        self._request_json(
            "scroll",
            timeout=timeout,
            x=int(x),
            y=int(y),
            deltaY=int(delta_y),
        )

    def drag(self, start_x, start_y, end_x, end_y, timeout=DEFAULT_TIMEOUT):
        self._request_json(
            "drag",
            timeout=timeout,
            startX=int(start_x),
            startY=int(start_y),
            endX=int(end_x),
            endY=int(end_y),
        )

    def refresh(self, timeout=DEFAULT_TIMEOUT):
        self._request_json("refresh", timeout=timeout)

    def get_quest_stats(self, timeout=DEFAULT_TIMEOUT):
        response = self._request_json("quest_stats", timeout=timeout)
        return response.get("data", {})

    def _request_json(self, command, timeout=DEFAULT_TIMEOUT, **payload):
        request_id = self._send_request(command, **payload)
        return self._wait_for_response(request_id, timeout)

    def _send_request(self, command, **payload):
        with self._condition:
            request_id = self._next_request_id
            self._next_request_id += 1

        message = {"id": request_id, "type": command}
        message.update(payload)
        self._send_packet(self.JSON_PACKET, json.dumps(message).encode("utf-8"))
        return request_id

    def _send_packet(self, packet_type, payload):
        sock = self._socket
        if sock is None:
            raise PoiClientError("Not connected to the POI interaction service")

        packet = bytes((packet_type,)) + payload
        with self._send_lock:
            try:
                sock.sendall(struct.pack("<I", len(packet)) + packet)
            except OSError as exc:
                self._set_receiver_error(exc)
                raise PoiClientError("Failed to send a request to POI") from exc

    def _wait_for_response(self, request_id, timeout):
        with self._condition:
            ready = self._condition.wait_for(
                lambda: (
                    request_id in self._responses
                    or self._receiver_error is not None
                    or self._socket is None
                ),
                timeout,
            )
            if not ready:
                raise PoiClientError("Timed out waiting for a response from POI")
            self._raise_receiver_error()
            response = self._responses.pop(request_id)

        if response.get("type") == "error":
            raise PoiClientError(response.get("message", "POI request failed"))
        return response

    def _wait_for_frame(self, request_id, timeout):
        with self._condition:
            ready = self._condition.wait_for(
                lambda: (
                    request_id in self._frames
                    or request_id in self._responses
                    or self._receiver_error is not None
                    or self._socket is None
                ),
                timeout,
            )
            if not ready:
                raise PoiClientError("Timed out waiting for a frame from POI")
            self._raise_receiver_error()
            if request_id in self._responses:
                response = self._responses.pop(request_id)
                raise PoiClientError(response.get("message", "POI capture failed"))
            return self._frames.pop(request_id)

    def _raise_receiver_error(self):
        if self._receiver_error is not None:
            raise PoiClientError(
                "POI interaction connection was closed"
            ) from self._receiver_error
        if self._socket is None:
            raise PoiClientError("POI interaction connection was closed")

    def _receive_loop(self, sock):
        try:
            while self._socket is sock:
                size_data = self._receive_exact(sock, 4)
                packet_size = struct.unpack("<I", size_data)[0]
                if packet_size < 1 or packet_size > self.MAX_PACKET_SIZE:
                    raise PoiClientError("POI returned an invalid packet size")
                packet = self._receive_exact(sock, packet_size)
                self._handle_packet(packet[0], packet[1:])
        except Exception as exc:
            if self._socket is sock:
                self._set_receiver_error(exc)

    def _receive_exact(self, sock, length):
        chunks = bytearray()
        while len(chunks) < length:
            chunk = sock.recv(length - len(chunks))
            if not chunk:
                raise PoiClientError("POI interaction connection was closed")
            chunks.extend(chunk)
        return bytes(chunks)

    def _handle_packet(self, packet_type, payload):
        if packet_type == self.JSON_PACKET:
            response = json.loads(payload.decode("utf-8"))
            request_id = int(response["id"])
            with self._condition:
                self._responses[request_id] = response
                self._condition.notify_all()
            return

        if packet_type == self.FRAME_PACKET:
            if len(payload) < 13:
                raise PoiClientError("POI returned an invalid frame header")
            request_id, width, height, channels = struct.unpack("<IIIB", payload[:13])
            with self._condition:
                self._frames[request_id] = (width, height, channels, payload[13:])
                self._condition.notify_all()
            return

        raise PoiClientError(f"POI returned unknown packet type {packet_type}")

    def _set_receiver_error(self, error):
        with self._condition:
            self._receiver_error = error
            self._condition.notify_all()
