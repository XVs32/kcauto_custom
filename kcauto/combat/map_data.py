from combat.node import MapNode, EmptyNode
from kca_enums.maps import MapEnum


class MapData(object):
    enum = None
    page = None
    enemy_context = []
    nodes = {}  # key(str) , value(MapNode)
    edges = {}

    def __init__(self, enum: MapEnum, data: dict):
        self.enum = enum
        self.page = data.get("page", 1)
        self.enemy_context = list(data.get("enemy_context", []))

        self.nodes = {}
        self.edges = {}

        for node_name in data["nodes"]:
            self.nodes[node_name] = MapNode(node_name, data["nodes"][node_name])

        for edge in data["edges"]:
            node_a = data["edges"][edge][0]
            node_b = data["edges"][edge][1]
            self.edges[int(edge)] = (
                self.nodes.get(node_a, EmptyNode(node_a)),
                self.nodes.get(node_b, EmptyNode(node_b)),
            )

    def is_node_exist(self, node_name: str) -> bool:
        return node_name in self.nodes
