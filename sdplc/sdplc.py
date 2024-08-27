from ast import mod
import asyncio
import logging
from math import inf
import ssl
from typing import List, NoReturn, Optional

import Akatosh
import yaml
from Akatosh.event import event
from Akatosh.universe import Mundus
from asyncua import ua
from pydantic import ValidationError
from pymodbus.constants import Endian
from pymodbus.server import (
    StartAsyncTcpServer,
    StartAsyncUdpServer,
    StartAsyncTlsServer,
)

from sdplc.modbus import decoder, encoder

from . import logger
from .modbus.server import modbusServer
from .modbus.client import modbusClient
from .opcua.server import opcuaServer
from .opcua.client import opcuaClient
from .schemas import Config, ModBusIPConfig, Node, OPCUAConfig


class SDPLC:

    def __init__(self) -> None:
        self.opcuaServer = opcuaServer
        self.opcuaClient = opcuaClient
        self.modbusServer = modbusServer
        self.modbusClient = modbusClient
        self.nodes: List[Node] = list()
        self.config: Config = Config(
            server="OPCUA",
            opcua_server_config=OPCUAConfig(
                url="opc.tcp://0.0.0.0:14840/ulfaric/SDPLC/",
                security_policy=[ua.SecurityPolicyType.NoSecurity],
            ),
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
                logger.warning(f"Invalid config file {config_file}, {e}.")
                raise e
            except ValidationError as e:
                logger.warning(f"Invalid config file {config_file}, {e}.")
                raise e

            if self.config.server == "OPCUA":
                if self.config.opcua_server_config:
                    self.opcuaServer.init(self.config.opcua_server_config.url)

                    @event(at=0, till=0, label="Start OPC UA Server", priority=0)
                    async def start_opcua_server() -> NoReturn:
                        if self.config.opcua_server_config is None:
                            raise ValueError("OPCUA configuration is missing.")

                        self.opcuaServer.server.set_security_policy(
                            self.config.opcua_server_config.security_policy
                        )
                        if (
                            self.config.opcua_server_config.private_key
                            and self.config.opcua_server_config.certificate
                        ):
                            await self.opcuaServer.server.load_private_key(
                                path_or_content=self.config.opcua_server_config.private_key
                            )
                            await self.opcuaServer.server.load_certificate(
                                path_or_content=self.config.opcua_server_config.certificate
                            )
                        logger.info("Starting OPC UA server...")
                        await self.opcuaServer.server.start()

            if self.config.server == "ModBus":
                if self.config.modbus_server_config:
                    self.modbusServer.config(
                        byte_order=(
                            Endian.BIG
                            if self.config.modbus_server_config.byte_order == "big"
                            else Endian.LITTLE
                        ),
                        word_order=(
                            Endian.BIG
                            if self.config.modbus_server_config.word_order == "big"
                            else Endian.LITTLE
                        ),
                    )

                    @event(at=0, till=0, label="Start Modbus Server", priority=0)
                    async def start_modbus_server() -> NoReturn:
                        if self.config.modbus_server_config is None:
                            raise ValueError("ModBus configuration is missing.")
                        self.modbusServer.init()
                        if isinstance(self.config.modbus_server_config, ModBusIPConfig):
                            if self.config.modbus_server_config.type == "tcp":
                                logger.info("Starting Modbus TCP server...")
                                await StartAsyncTcpServer(
                                    context=self.modbusServer.server_context,
                                    identity=self.modbusServer.identity,
                                    address=(
                                        self.config.modbus_server_config.address,
                                        self.config.modbus_server_config.port,
                                    ),
                                )
                            elif self.config.modbus_server_config.type == "udp":
                                logger.info("Starting Modbus UDP server...")
                                await StartAsyncUdpServer(
                                    context=self.modbusServer.server_context,
                                    identity=self.modbusServer.identity,
                                    address=(
                                        self.config.modbus_server_config.address,
                                        self.config.modbus_server_config.port,
                                    ),
                                )
                            elif self.config.modbus_server_config.type == "tls":
                                logger.info("Starting Modbus TLS server...")
                                sslctx = ssl.create_default_context(
                                    ssl.Purpose.CLIENT_AUTH
                                )
                                if (
                                    self.config.modbus_server_config.certificate
                                    and self.config.modbus_server_config.key
                                ):
                                    sslctx.load_cert_chain(
                                        self.config.modbus_server_config.certificate,
                                        self.config.modbus_server_config.key,
                                    )
                                if self.config.modbus_server_config.ca:
                                    sslctx.load_verify_locations(
                                        self.config.modbus_server_config.ca
                                    )
                                await StartAsyncTlsServer(
                                    context=self.modbusServer.server_context,
                                    identity=self.modbusServer.identity,
                                    address=(
                                        self.config.modbus_server_config.address,
                                        self.config.modbus_server_config.port,
                                    ),
                                    sslctx=sslctx,
                                )

            if self.config.client == "OPCUA":
                if self.config.opcua_client_config:
                    asyncio.run(
                        self.opcuaClient.config(self.config.opcua_client_config)
                    )
            if self.config.client == "ModBus":
                if self.config.modbus_client_config:
                    self.modbusClient.config(self.config.modbus_client_config)
            if self.config.nodes:
                for node in self.config.nodes:
                    self.add_Node(node)

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
        if self.config.server == "OPCUA":
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

        if self.config.client == "OPCUA":
            asyncio.run(self.opcuaClient.connect())
            if node.opcua:
                node.opcua.node_id = asyncio.run(
                    self.opcuaClient.browse_and_find_node(
                        node.opcua.node_qualified_name
                    )
                )
                logger.debug(
                    f"AllocatedNode {node.qualified_name} OPCUA with node id: {node.opcua.node_id}"
                )
                
        if self.config.server == "ModBus":
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
            if self.config.server == "OPCUA":
                opcua_value = await self.opcuaServer.variables[
                    node.qualified_name
                ].read_value()
                if opcua_value is not None:
                    if opcua_value != node.value:
                        node.value = opcua_value
                        logger.warning(
                            f"Node {node.qualified_name} value updated to {node.value} by external OPC UA source"
                        )
                        if self.config.client == "ModBus":
                            if node.modbus:
                                self.modbusClient.connect()
                                if node.modbus.type == "c":
                                    self.modbusClient.write_coil(
                                        node.modbus.address,
                                        bool(node.value),
                                        node.modbus.slave,
                                    )
                                elif node.modbus.type == "h":
                                    if self.modbusClient._config:
                                        byte_order = (
                                            Endian.BIG
                                            if self.modbusClient._config.byte_order
                                            == "big"
                                            else Endian.LITTLE
                                        )
                                        word_order = (
                                            Endian.BIG
                                            if self.modbusClient._config.word_order
                                            == "big"
                                            else Endian.LITTLE
                                        )
                                        values = encoder(
                                            node.value,
                                            node.modbus.register_size,
                                            byte_order,
                                            word_order,
                                        )
                                        self.modbusClient.write_holding_registers(
                                            node.modbus.address,
                                            values,
                                            node.modbus.slave,
                                        )
                                    else:
                                        raise RuntimeError(
                                            f"Modbus client configuration is missing! Failed to write Node {node.qualified_name} value!"
                                        )
                                self.modbusClient.close()
                                logger.warning(
                                    f"Node {node.qualified_name} value pushed to external Modbus sink"
                                )
                else:
                    raise RuntimeError(
                        f"Fail to read Node {node.qualified_name} OPCUA value!"
                    )

            if self.config.server == "ModBus":
                if node.modbus:
                    modbus_value = None
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
                    if modbus_value is not None:
                        if modbus_value != node.value:
                            node.value = modbus_value
                            logger.warning(
                                f"Node {node.qualified_name} value updated to {node.value} by external Modbus source"
                            )
                            if self.config.client == "OPCUA":
                                pass
                    else:
                        raise RuntimeError(
                            f"Fail to read Node {node.qualified_name} Modbus value!"
                        )
                else:
                    raise RuntimeError(
                        f"Node {node.qualified_name} has no Modbus config but Modbus is set as the server!"
                    )

    async def read_node(self, qualified_name: str):
        """
        read_variable Reads the value of a variable.

        The value of the variable is read from all south interfaces.

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
        if self.config.client == "OPCUA":
            if node.opcua:
                if node.opcua.node_id is None:
                    raise RuntimeError(f"Node {node.qualified_name} OPCUA node id is not allocated!")
                node.value = asyncio.run(self.opcuaClient.read(node.opcua.node_id))
            else:
                raise RuntimeError(f"Node {node.qualified_name} has no OPCUA config but OPCUA is set as the client!")
        if self.config.client == "ModBus":
            if node.modbus:
                self.modbusClient.connect()
                if node.modbus.type == "c":
                    modbus_response = self.modbusClient.read_coils(
                        node.modbus.address, 1, node.modbus.slave
                    )
                    if modbus_response.isError():
                        raise RuntimeError(
                            f"Failed to read Node {node.qualified_name} value!"
                        )
                    else:
                        node.value = bool(modbus_response.bits[0])
                elif node.modbus.type == "d":
                    modbus_response = self.modbusClient.read_discrete_inputs(
                        node.modbus.address, 1, node.modbus.slave
                    )
                    if modbus_response.isError():
                        raise RuntimeError(
                            f"Failed to read Node {node.qualified_name} value!"
                        )
                    else:
                        node.value = bool(modbus_response.bits[0])
                elif node.modbus.type == "h":
                    modbus_response = self.modbusClient.read_holding_registers(
                        node.modbus.address,
                        node.modbus.register_size // 16,
                        node.modbus.slave,
                    )
                    if modbus_response.isError():
                        raise RuntimeError(
                            f"Failed to read Node {node.qualified_name} value!"
                        )
                    else:
                        node.value = decoder(
                            modbus_response.registers,
                            "int" if isinstance(node.value, int) else "float",
                            (
                                Endian.BIG
                                if self.modbusClient._config
                                and self.modbusClient._config.byte_order == "big"
                                else Endian.LITTLE
                            ),
                            (
                                Endian.BIG
                                if self.modbusClient._config
                                and self.modbusClient._config.word_order == "big"
                                else Endian.LITTLE
                            ),
                        )
                elif node.modbus.type == "i":
                    modbus_response = self.modbusClient.read_input_registers(
                        node.modbus.address,
                        node.modbus.register_size // 16,
                        node.modbus.slave,
                    )
                    if modbus_response.isError():
                        raise RuntimeError(
                            f"Failed to read Node {node.qualified_name} value! {modbus_response}"
                        )
                    else:
                        node.value = decoder(
                            modbus_response.registers,
                            "int" if isinstance(node.value, int) else "float",
                            (
                                Endian.BIG
                                if self.modbusClient._config
                                and self.modbusClient._config.byte_order == "big"
                                else Endian.LITTLE
                            ),
                            (
                                Endian.BIG
                                if self.modbusClient._config
                                and self.modbusClient._config.word_order == "big"
                                else Endian.LITTLE
                            ),
                        )
                self.modbusClient.close()
            else:
                raise RuntimeError(f"Node {node.qualified_name} has no Modbus config but Modbus is set as the client!")
        return node.value

    async def write_node(self, qualified_name: str, value: int | float | bool):
        """
        write_variable Writes a value to a variable.

        The value is written to all south interfaces.

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
        if self.config.server == "OPCUA":
            if node.opcua:
                await self.opcuaServer.variables[node.qualified_name].write_value(
                    node.value
                )
            else:
                raise RuntimeError(f"Node {node.qualified_name} has no OPCUA config but OPCUA is set as the server!")
        if self.config.server == "ModBus":
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
            else:
                raise RuntimeError(f"Node {node.qualified_name} has no Modbus config but Modbus is set as the server!")

        if self.config.client == "OPCUA":
            if node.opcua:
                if node.opcua.node_id is None:
                    raise RuntimeError(f"Node {node.qualified_name} OPCUA node id is not allocated!")
                await self.opcuaClient.write(node.opcua.node_id, node.value)
            else:
                raise RuntimeError(f"Node {node.qualified_name} has no OPCUA config but OPCUA is set as the client!")

        if self.config.client == "ModBus":
            if node.modbus:
                self.modbusClient.connect()
                if node.modbus.type == "c":
                    self.modbusClient.write_coil(
                        node.modbus.address, bool(node.value), node.modbus.slave
                    )
                elif node.modbus.type == "h":
                    if self.modbusClient._config:
                        byte_order = (
                            Endian.BIG
                            if self.modbusClient._config.byte_order == "big"
                            else Endian.LITTLE
                        )
                        word_order = (
                            Endian.BIG
                            if self.modbusClient._config.word_order == "big"
                            else Endian.LITTLE
                        )
                        values = encoder(
                            node.value,
                            node.modbus.register_size,
                            byte_order,
                            word_order,
                        )
                        self.modbusClient.write_holding_registers(
                            node.modbus.address, values, node.modbus.slave
                        )
                    else:
                        raise RuntimeError(
                            f"Modbus client configuration is missing! Failed to write Node {node.qualified_name} value!"
                        )
                self.modbusClient.close()
            else:
                raise RuntimeError(f"Node {node.qualified_name} has no Modbus config but Modbus is set as the client!")


simPLC = SDPLC()
