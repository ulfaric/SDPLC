from sdplc.opcua import server

server.init()

namespace = "http://example.org"
server.register_namespace(namespace)
node = server.register_node("Tank", namespace)
server.register_variable("Tank Level", node=node, writeable=True, value=0)
server.register_variable("Tank Temperature", node_qualified_name="Tank", writeable=True, value=0)

server.start()