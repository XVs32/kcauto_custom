import json
import socket
import struct
import sys
import threading
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "kcauto"))

from config.general import ConfigGeneral  # noqa: E402
from util.poi_client import PoiClient  # noqa: E402


def receive_exact(sock, length):
    data = bytearray()
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise EOFError
        data.extend(chunk)
    return bytes(data)


def send_packet(sock, packet_type, payload):
    packet = bytes((packet_type,)) + payload
    sock.sendall(struct.pack("<I", len(packet)) + packet)


class FakePoiServer:
    def __init__(self):
        self.commands = []
        self.socket = socket.socket()
        self.socket.bind(("127.0.0.1", 0))
        self.socket.listen(1)
        self.port = self.socket.getsockname()[1]
        self.thread = threading.Thread(target=self.run, daemon=True)

    def start(self):
        self.thread.start()

    def close(self):
        self.socket.close()

    def run(self):
        client, _ = self.socket.accept()
        with client:
            while True:
                try:
                    packet_size = struct.unpack("<I", receive_exact(client, 4))[0]
                    packet = receive_exact(client, packet_size)
                except (EOFError, OSError, struct.error):
                    return
                command = json.loads(packet[1:].decode("utf-8"))
                self.commands.append(command)
                request_id = command["id"]

                if command["type"] == "capture":
                    bitmap = bytes((0, 0, 255, 255, 0, 255, 0, 255))
                    frame = struct.pack("<IIIB", request_id, 2, 1, 4) + bitmap
                    send_packet(client, PoiClient.FRAME_PACKET, frame)
                    continue

                response = {"id": request_id, "type": "ok"}
                if command["type"] == "hello":
                    response.update(type="hello", protocol=1)
                elif command["type"] == "ping":
                    response["type"] = "pong"
                elif command["type"] == "quest_stats":
                    response.update(type="quest_stats", data={"201": {"state": 2}})
                send_packet(
                    client,
                    PoiClient.JSON_PACKET,
                    json.dumps(response).encode("utf-8"),
                )


class PoiClientTest(unittest.TestCase):
    def setUp(self):
        self.server = FakePoiServer()
        self.server.start()
        self.client = PoiClient(port=self.server.port)
        self.client.connect()

    def tearDown(self):
        self.client.close()
        self.server.close()

    def test_protocol_round_trip(self):
        self.assertTrue(self.client.health_check())
        image = self.client.capture()
        self.assertEqual(image.size, (2, 1))
        self.assertEqual(image.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(image.getpixel((1, 0)), (0, 255, 0))
        self.assertEqual(self.client.get_quest_stats(), {"201": {"state": 2}})

        self.client.click(100.8, 200.2)
        self.assertEqual(self.server.commands[-1]["x"], 100)
        self.assertEqual(self.server.commands[-1]["y"], 200)

        self.client.scroll(300.9, 400.1, 120)
        self.assertEqual(self.server.commands[-1]["type"], "scroll")
        self.assertEqual(self.server.commands[-1]["deltaY"], 120)

    def test_close_marks_client_disconnected(self):
        self.client.close()
        self.assertFalse(self.client.connected)


class ConfigGeneralTest(unittest.TestCase):
    def test_old_config_uses_poi_port_defaults(self):
        config = ConfigGeneral(
            {
                "general.jst_offset": 0,
                "general.interaction_mode": "poi",
                "general.chrome_dev_port": 9222,
            }
        )
        self.assertEqual(config.poi_api_port, 9223)
        self.assertEqual(config.poi_control_port, 38591)


if __name__ == "__main__":
    unittest.main()
