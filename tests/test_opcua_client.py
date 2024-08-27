import unittest
import asyncio
from asyncua import Server
from sdplc.opcua.client import SDPLCOPCUAClient
from sdplc.opcua.schemas import OPCUAConfig
from sdplc import logger

class TestOPCUAClient(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.loop = asyncio.get_event_loop()
        cls.server = Server()
        cls.loop.run_until_complete(cls.server.init())
        cls.server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
        uri = "http://example.org"
        cls.idx = cls.loop.run_until_complete(cls.server.register_namespace(uri))
        objects = cls.server.nodes.objects
        cls.test_obj = cls.loop.run_until_complete(objects.add_object(cls.idx, "test"))
        cls.test_var = cls.loop.run_until_complete(cls.test_obj.add_variable(cls.idx, "testVariable", 0))
        cls.loop.run_until_complete(cls.test_var.set_writable())
        cls.loop.run_until_complete(cls.server.start())

    @classmethod
    def tearDownClass(cls):
        cls.loop.run_until_complete(cls.server.stop())

    def setUp(self):
        self.client = SDPLCOPCUAClient()
        config = OPCUAConfig(url="opc.tcp://localhost:4840/freeopcua/server/", security_policy=[0])
        self.loop.run_until_complete(self.client.config(config))
        self.loop.run_until_complete(self.client.connect())

    def tearDown(self):
        self.loop.run_until_complete(self.client.disconnect())

    def test_browse_and_find_node(self):
        self.node_id = self.loop.run_until_complete(self.client.browse_and_find_node("testVariable"))
        logger.info(f"Node ID: {self.node_id}") 
        self.assertIsNotNone(self.node_id, "Node 'test' should be found")
        self.assertEqual(self.node_id, "ns=2;i=2", "Node ID should be 'ns=2;i=2'")
    
    def test_read_value(self):
        value = self.loop.run_until_complete(self.client.read("ns=2;i=2"))
        logger.info(f"Value: {value}")
        self.assertEqual(value, 0, "Node 'test' should be 0")

    def test_write_value(self):
        self.loop.run_until_complete(self.client.write("ns=2;i=2", 1))
        value = self.loop.run_until_complete(self.client.read("ns=2;i=2"))
        logger.info(f"Value: {value}")
        self.assertEqual(value, 1, "Node 'test' should be 1")

if __name__ == "__main__":
    unittest.main()