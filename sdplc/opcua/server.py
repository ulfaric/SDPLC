import asyncio
import datetime
import logging
import math
from typing import Any, Dict, List, NoReturn, Optional
from urllib.parse import urlparse, urlunparse

import Akatosh
from Akatosh.event import event
from Akatosh.universe import Mundus
from asyncua import Node, Server, ua
from asyncua.server.user_managers import UserManager
from asyncua.server.users import User, UserRole

from .. import logger


class simOPCUA_UserManager(UserManager):

    def __init__(self) -> None:
        super().__init__()

    def get_user(self, iserver=None, username=None, password=None, certificate=None):
        return User(role=UserRole.Admin)


class SDPLCOPCUAServer:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:
        """Create a simulated PLC based on OPC UA."""
        self.server = Server(user_manager=simOPCUA_UserManager)
        self.endpont = None
        self.config = None
        self.namespaces: Dict[str, int] = {}
        self.nodes: Dict[str, Node] = {}
        self.variables: Dict[str, Node] = {}

    def register_namespace(self, namespace: str) -> int | None:
        """Register a namespace.

        Args:
            namespace (str): the namespace to be registered.

        Returns:
            int | None: returns the index of the registered namespace.
        """
        try:
            urlparse(url=namespace)
            index: int = asyncio.run(main=self.server.register_namespace(uri=namespace))
            self.namespaces[namespace] = index
            logger.info(msg=f"Namespace {namespace} registered with index {index}.")
            return index
        except ValueError:
            logger.error(msg=f"Invalid namespace: {namespace}.")
        except Exception as e:
            logger.error(msg=f"Error: {e}")

    def register_node(self, qualified_name: str, namespace: str) -> Node | None:
        """Register a node.

        Args:
            qualified_name (str): the qualified name of the node.
            namespace (str): the namespace of the node.

        Returns:
            Node | None: returns the registered node.
        """
        try:
            index: int = self.namespaces[namespace]
            node: Node = asyncio.run(
                self.server.nodes.objects.add_object(nodeid=index, bname=qualified_name)
            )
            self.nodes[qualified_name] = node
            logger.info(
                f"Node {qualified_name} registered in namespace {namespace}, node id: {node.nodeid}."
            )
            return node
        except KeyError:
            logger.error(f"Namespace not found: {namespace}.")
        except Exception as e:
            logger.error(f"Error: {e}")

    def register_variable(
        self,
        qualified_name: str,
        writeable: bool = False,
        value: Optional[Any] = None,
        node: Optional[Node] = None,
        node_qualified_name: Optional[str] = None,
    ) -> Node | None:
        """Register a variable.

        Args:
            qualified_name (str): the qualified name of the variable.
            writeable (bool, optional): set to true if the variable should be writeable. Defaults to False.
            value (Optional[Any], optional): the initial value of the variable. Defaults to None.
            node (Optional[Node], optional): the node of the variable. Defaults to None.
            node_qualified_name (Optional[str], optional): the qualified name of the node for the variable. Defaults to None.

        Raises:
            NodeNotDefined: return the registered variable.
        """

        class NodeNotDefined(Exception):
            pass

        class NodeNotFound(Exception):
            pass

        try:
            if node:
                var: Node = asyncio.run(
                    node.add_variable(
                        nodeid=node.nodeid.NamespaceIndex,
                        bname=qualified_name,
                        val=value,
                    )
                )
                if writeable:
                    asyncio.run(var.set_writable())
                self.variables[qualified_name] = var
                logger.info(
                    f"Variable {qualified_name} registered in node {node.nodeid} at namespace {node.nodeid.NamespaceIndex}."
                )
                return var

            if node_qualified_name:
                if node_qualified_name not in self.nodes.keys():
                    raise NodeNotFound
                node = self.nodes[node_qualified_name]
                var: Node = asyncio.run(
                    node.add_variable(
                        nodeid=node.nodeid.NamespaceIndex,
                        bname=qualified_name,
                        val=value,
                    )
                )
                if writeable:
                    asyncio.run(var.set_writable())
                self.variables[qualified_name] = var
                logger.info(
                    f"Variable {qualified_name} registered in node {node_qualified_name} at namespace {self.nodes[node_qualified_name].nodeid.NamespaceIndex}."
                )
                return var

            if node is None and node_qualified_name is None:
                raise NodeNotDefined

        except NodeNotDefined:
            logger.error(msg=f"Node not defined.")
        except NodeNotFound:
            logger.error(msg=f"Node not found: {node_qualified_name}.")
        except Exception as e:
            logger.error(msg=f"Error: {e}")

    def init(
        self,
        endpoint: Optional[str] = None,
        application_uri: Optional[str] = None,
    ) -> None:
        """Initialize the server with given endpoint and configuration file."""

        async def _config() -> None:

            if application_uri:
                await self.server.set_application_uri(uri=application_uri)
            else:
                await self.server.set_application_uri(uri="uri:ulfaric:SDPLC")

            await self.server.set_build_info(
                product_uri="uri:ulfaric:SDPLC",
                manufacturer_name="SDPLC",
                product_name="SDPLC",
                software_version="1.0.0",
                build_number="Alpha",
                build_date=datetime.datetime.now(),
            )

            self.server.set_server_name(name="SDICS SimPLC")

        if endpoint:
            self.endpont = urlparse(url=endpoint)
            self.server.set_endpoint(url=urlunparse(self.endpont))
        else:
            self.endpont = urlparse("opc.tcp://0.0.0.0:14840/ulfaric/SDPLC/")
            self.server.set_endpoint(url=urlunparse(self.endpont))

        asyncio.run(main=self.server.init())
        asyncio.run(main=_config())

    def start(
        self,
        security_policy: Optional[List[ua.SecurityPolicyType]] = None,
        private_key: Optional[str] = None,
        certificate: Optional[str] = None,
    ) -> None:
        """Start the server with given security type, private key and certificate.

        Args:
            security_type (Optional[List[ua.SecurityPolicyType]], optional): the OPC UA security type. Defaults to None.
            private_key (Optional[str], optional): the private key. Defaults to None.
            certificate (Optional[str], optional): the certificate. Defaults to None.
        """

        @event(at=0, till=0, label="Start OPC UA Server")
        async def _start() -> NoReturn:
            if security_policy:
                self.server.set_security_policy(security_policy)
            else:
                self.server.set_security_policy(
                    security_policy=[ua.SecurityPolicyType.NoSecurity]
                )
            if private_key and certificate:
                await self.server.load_private_key(path_or_content=private_key)
                await self.server.load_certificate(path_or_content=certificate)
            await self.server.start()

        Akatosh.logger.setLevel(level=logging.INFO)
        Mundus.enable_realtime()
        asyncio.run(main=Mundus.simulate(till=math.inf))


opcuaServer = SDPLCOPCUAServer()
