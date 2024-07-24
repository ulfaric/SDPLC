import asyncio
import logging
from math import e, inf
from typing import Dict, List, NoReturn, Optional

import Akatosh
import yaml
from Akatosh.event import event
from Akatosh.universe import Mundus
from asyncua import ua
from pymodbus.constants import Endian
from pymodbus.server import StartAsyncTcpServer
from pydantic import ValidationError

from sdplc import modbus

from . import logger
from .modbus.server import modbusServer
from .opcua.server import opcuaServer
from .schemas import ModBusConfig, Node, Config, OPCUAConfig


class SDPLC:

    def __init__(self) -> None:
        self.opcuaServer = opcuaServer
        self.modbusServer = modbusServer
        self.nodes: List[Node] = list()
        self.config: Config = Config(
            north=["OPCUA", "ModBus"],
            south=[],
            modbus=ModBusConfig(
                address="0.0.0.0",
                port=1502,
            ),
            opcua=OPCUAConfig(
                url="opc.tcp://0.0.0.0:14840/ulfaric/SDPLC/",
                security_policy=[ua.SecurityPolicyType.NoSecurity],
            ),
            nodes=None,
        )

    def init(
        self,
        config_file: Optional[str] = "config.yaml",
    ) -> None:
        if config_file:
            try:
                config = yaml.safe_load(open(config_file, "r"))
                self.config = Config(**config)
            except FileNotFoundError as e:
                logger.warning(
                    f"Config file {config_file} not found, default configuration will be used instead."
                )
            except yaml.YAMLError as e:
                logger.warning(
                    f"Invalid config file {config_file}, {e}. Default configuration will be used instead."
                )
            except ValidationError as e:
                logger.warning(
                    f"Invalid config file {config_file}, {e}. Default configuration will be used instead."
                )

            if self.config.north:
                if "OPCUA" in self.config.north:
                    if self.config.opcua:
                        self.opcuaServer.init(self.config.opcua.url)

                        @event(at=0, till=0, label="Start OPC UA Server")
                        async def start_opcua_server() -> NoReturn:
                            if self.config.opcua is None:
                                raise ValueError("OPCUA configuration is missing.")

                            self.opcuaServer.server.set_security_policy(
                                self.config.opcua.security_policy
                            )
                            if (
                                self.config.opcua.private_key
                                and self.config.opcua.certificate
                            ):
                                await self.opcuaServer.server.load_private_key(
                                    path_or_content=self.config.opcua.private_key
                                )
                                await self.opcuaServer.server.load_certificate(
                                    path_or_content=self.config.opcua.certificate
                                )
                            logger.info("Starting OPC UA server...")
                            await self.opcuaServer.server.start()

                if self.config.nodes:
                    for node in self.config.nodes:
                        self.add_Node(node)

                if "ModBus" in self.config.north:
                    if self.config.modbus:
                        self.modbusServer.config(
                            byte_order=(
                                Endian.BIG
                                if self.config.modbus.byte_order == "big"
                                else Endian.LITTLE
                            ),
                            word_order=(
                                Endian.BIG
                                if self.config.modbus.word_order == "big"
                                else Endian.LITTLE
                            ),
                        )

                        @event(at=0, till=0, label="Start Modbus Server")
                        async def start_modbus_server() -> NoReturn:
                            if self.config.modbus is None:
                                raise ValueError("ModBus configuration is missing.")
                            self.modbusServer.init()
                            logger.info("Starting Modbus server...")
                            await StartAsyncTcpServer(
                                context=self.modbusServer.server_context,
                                identity=self.modbusServer.identity,
                                address=(
                                    self.config.modbus.address,
                                    self.config.modbus.port,
                                ),
                            )

    def start(self) -> None:
        Akatosh.logger.setLevel(level=logging.INFO)
        Mundus.enable_realtime()
        asyncio.run(main=Mundus.simulate(till=inf))

    def add_Node(self, node: Node) -> None:
        """
        add_variable Creates a variable in the Modbus server and registers it in the OPC UA server.

        The variable is created in the Modbus server and registered in the OPC UA server. The variable is then added to the list of variables in the PLC and a synchronization event is created to keep the OPC UA variable in sync with the Modbus variable.

        Args:
            variable (SimVariable): the variable to be added.

        Raises:
            ValueError: raised when the value type is invalid for the variable type, or when the register size is invalid for holding and input registers.
        """
        self.nodes.append(node)
        if self.config.north and "OPCUA" in self.config.north:
            # check if the OPC UA namespace exists
            # Each modbus slave has its own namespace and a root node with the slave id as qualified name
            if node.opcua:
                namespace = f"http://ulfaric/SDPLC/{node.opcua.namespace}"
                if namespace not in self.opcuaServer.namespaces.keys():
                    self.opcuaServer.register_namespace(namespace)
                    self.opcuaServer.register_node(
                        qualified_name=f"{node.opcua.node_qualified_name}",
                        namespace=namespace,
                    )
                self.opcuaServer.register_variable(
                    node.qualified_name,
                    True,
                    node.value,
                    self.opcuaServer.nodes[node.opcua.node_qualified_name],
                )

        if self.config.north and "ModBus" in self.config.north:
            if node.modbus:
                # check if the modbus slave exists
                if node.modbus.slave not in self.modbusServer.slaves.keys():
                    # create the modbus slave if not exists
                    self.modbusServer.create_slave(node.modbus.slave)

                if node.modbus.type == "c":
                    self.modbusServer.create_coil(
                        node.modbus.slave, node.modbus.address, bool(node.value)
                    )
                elif node.modbus.type == "d":
                    if isinstance(node.value, bool):
                        self.modbusServer.create_discrete_input(
                            node.modbus.slave, node.modbus.address, bool(node.value)
                        )
                elif node.modbus.type == "h":
                    self.modbusServer.create_holding_register(
                        node.modbus.slave,
                        node.modbus.address,
                        node.value,
                        node.modbus.register_size,
                    )
                elif node.modbus.type == "i":
                    self.modbusServer.create_input_register(
                        node.modbus.slave,
                        node.modbus.address,
                        node.value,
                        node.modbus.register_size,
                    )

        @event(
            at=0,
            till=inf,
            label=f"Sync Node {node.qualified_name}",
            priority=1,
        )
        async def sync_node():

            opcua_value = await self.opcuaServer.variables[
                node.qualified_name
            ].read_value()
            modbus_value = None
            if self.config.north and "ModBus" in self.config.north:
                if node.modbus:
                    if node.modbus.type == "c":
                        modbus_value = self.modbusServer.read_coil(
                            node.modbus.slave, node.modbus.address
                        )
                    elif node.modbus.type == "d":
                        modbus_value = self.modbusServer.read_discrete_input(
                            node.modbus.slave, node.modbus.address
                        )
                    elif node.modbus.type == "h":
                        modbus_value = self.modbusServer.read_holding_register(
                            node.modbus.slave, node.modbus.address
                        )
                    elif node.modbus.type == "i":
                        modbus_value = self.modbusServer.read_input_register(
                            node.modbus.slave, node.modbus.address
                        )

            if opcua_value != node.value:
                node.value = opcua_value
                if self.config.north and "ModBus" in self.config.north:
                    if node.modbus:
                        if node.modbus.type == "c":
                            self.modbusServer.write_coil(
                                node.modbus.slave,
                                node.modbus.address,
                                bool(node.value),
                            )
                        elif node.modbus.type == "d":
                            self.modbusServer.write_discrete_input(
                                node.modbus.slave,
                                node.modbus.address,
                                bool(node.value),
                            )
                        elif node.modbus.type == "h":
                            self.modbusServer.write_holding_register(
                                node.modbus.slave, node.modbus.address, node.value
                            )
                        elif node.modbus.type == "i":
                            self.modbusServer.write_input_register(
                                node.modbus.slave, node.modbus.address, node.value
                            )
                logger.warning(
                    f"Node  {node.qualified_name} OPCUA value updated to {opcua_value} by external source"
                )

            if modbus_value is not None:
                if modbus_value != node.value:
                    node.value = modbus_value
                    if self.config.north and "OPCUA" in self.config.north:
                        if node.opcua:
                            await self.opcuaServer.variables[
                                node.qualified_name
                            ].write_value(node.value)
                    logger.warning(f"Node  {node.qualified_name} Modbus value updated to {modbus_value} by external source")

    async def read_node(self, qualified_name: str):
        """
        read_variable Reads the value of a variable.

        The value of the variable is read from the OPC UA server.

        Args:
            qualified_name (str): the qualified name of the variable to be read.

        Raises:
            RuntimeError: raise if the variable is not found.
            ValueError: raise if the variable type is invalid.

        Returns:
            bool | int | float: the value of the variable.
        """
        node = next(
            (node for node in self.nodes if node.qualified_name == qualified_name),
            None,
        )
        if node is None:
            raise RuntimeError(f"Node {node} not found.")
        return node.value

    async def write_node(self, qualified_name: str, value: int | float | bool):
        """
        write_variable Writes a value to a variable.

        The value is written to the Modbus server.

        Args:
            qualified_name (str): the qualified name of the variable to be written.
            value (int | float | bool): the value to be written.

        Raises:
            ValueError: raised if the variable is not found, or if the value type is invalid for the variable type.
        """
        node = next(
            (var for var in self.nodes if var.qualified_name == qualified_name),
            None,
        )
        if node is None:
            raise ValueError(f"Node {node} not found.")
        node.value = value
        if self.config.north and "OPCUA" in self.config.north:
            if node.opcua:
                await self.opcuaServer.variables[node.qualified_name].write_value(
                    node.value
                )
        if self.config.north and "ModBus" in self.config.north:
            if node.modbus:
                if node.modbus.type == "c":
                    self.modbusServer.write_coil(
                        node.modbus.slave,
                        node.modbus.address,
                        bool(node.value),
                    )
                elif node.modbus.type == "d":
                    self.modbusServer.write_discrete_input(
                        node.modbus.slave,
                        node.modbus.address,
                        bool(node.value),
                    )
                elif node.modbus.type == "h":
                    self.modbusServer.write_holding_register(
                        node.modbus.slave, node.modbus.address, node.value
                    )
                elif node.modbus.type == "i":
                    self.modbusServer.write_input_register(
                        node.modbus.slave, node.modbus.address, node.value
                    )


simPLC = SDPLC()
