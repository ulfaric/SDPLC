from sdplc.opcua.server import opcuaServer

opcuaServer.init()

namespace = "http://example.org"
opcuaServer.register_namespace(namespace)
node = opcuaServer.register_node("Tank", namespace)
opcuaServer.register_variable("Tank Level", node=node, writeable=True, value=0)
opcuaServer.register_variable(
    "Tank Temperature", node_qualified_name="Tank", writeable=True, value=0
)

opcuaServer.start()
