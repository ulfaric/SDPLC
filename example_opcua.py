from sdplc.opcua import opcua

opcua.init()

namespace = "http://example.org"
opcua.register_namespace(namespace)
node = opcua.register_node("Tank", namespace)
# opcua.register_variable("Tank Level", node=node, writeable=True, value=0)
opcua.register_variable("Tank Temperature", node_qualified_name="Tank", writeable=True, value=0)

opcua.start()