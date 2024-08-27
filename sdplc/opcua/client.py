from typing import Any, List
from asyncua import Client, ua, Node
from .schemas import OPCUAConfig
from .. import logger

class SDPLCOPCUAClient:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:
        self.client: Client = None  # type: ignore

    async def config(
        self,
        config: OPCUAConfig,
    ) -> None:
        self.client = Client(url=config.url)
        policy_map = {
            0: ua.SecurityPolicyType.NoSecurity,
            1: ua.SecurityPolicyType.Basic128Rsa15_Sign,
            2: ua.SecurityPolicyType.Basic128Rsa15_SignAndEncrypt,
            3: ua.SecurityPolicyType.Basic256_Sign,
            4: ua.SecurityPolicyType.Basic256_SignAndEncrypt,
            5: ua.SecurityPolicyType.Basic256Sha256_Sign,
            6: ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt,
            7: ua.SecurityPolicyType.Aes128Sha256RsaOaep_Sign,
            8: ua.SecurityPolicyType.Aes128Sha256RsaOaep_SignAndEncrypt,
            9: ua.SecurityPolicyType.Aes256Sha256RsaPss_Sign,
            10: ua.SecurityPolicyType.Aes256Sha256RsaPss_SignAndEncrypt,
        }
        security_policy = None
        certificate = None
        private_key = None
        if config.security_policy is not None:
            security_policy = [policy_map[policy] for policy in config.security_policy]
            if config.certificate is not None:
                certificate = config.certificate
            if config.private_key is not None:
                private_key = config.private_key
        if security_policy is not None and certificate is not None and private_key is not None:
            await self.client.set_security(
                policy=security_policy,  # type: ignore
                certificate=certificate,
                private_key=private_key,
            )
            await self.client.load_client_certificate(path=certificate)
            await self.client.load_private_key(path=private_key)  # type: ignore

    async def connect(self) -> None:
        await self.client.connect()

    async def disconnect(self) -> None:
        await self.client.disconnect()

    async def read(self, nodeid: str) -> Any:
        await self.connect()
        node = self.client.get_node(nodeid)
        value = await node.read_value()
        await self.disconnect()
        return value

    async def write(self, nodeid: str, value: Any) -> None:
        await self.connect()
        node = self.client.get_node(nodeid)
        await node.write_value(value)
        await self.disconnect()

    async def browse_and_find_node(self, browse_name: str):
        root = self.client.nodes.root
        objects = self.client.nodes.objects
        visited_nodes = set()

        async def recursive_browse(node: Node, browse_name: str):
            if node.nodeid in visited_nodes:
                return None
            visited_nodes.add(node.nodeid)

            references = await node.get_references(ua.BrowseDirection.Forward)
            for ref in references:
                child_node = self.client.get_node(ref.NodeId)
                child_browse_name = await child_node.read_browse_name()
                if child_browse_name.Name == browse_name:
                    return child_node
                found_node = await recursive_browse(child_node, browse_name)
                if found_node:
                    return found_node
            return None

        found_node = await recursive_browse(objects, browse_name)
        if found_node:
            node_id = found_node.nodeid.to_string()
            return node_id
        else:
            return None

opcuaClient = SDPLCOPCUAClient()
