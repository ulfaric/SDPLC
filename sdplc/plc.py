import asyncio
import logging
from math import inf
from typing import Dict, List, NoReturn, Optional

import Akatosh
import yaml
from Akatosh.event import event
from Akatosh.universe import Mundus
from asyncua import ua
from pymodbus.constants import Endian
from pymodbus.server import StartAsyncTcpServer

from . import logger
from .modbus import modbus
from .opcua import opcua
from .schemas import SimVariable


class SDPLC:

    def __init__(self) -> None:
        self.opcua = opcua
        self.modbus = modbus
        self.variables: List[SimVariable] = list()

    def init(
        self,
        opcua_endpoint: Optional[str] = "opc.tcp://0.0.0.0:14840/ulfaric/SDPLC/",
        security_policy: Optional[List[ua.SecurityPolicyType]] = None,
        private_key: Optional[str] = None,
        certificate: Optional[str] = None,
        modbus_address: Optional[str] = "0.0.0.0",
        modbus_port: Optional[int] = 1502,
        config_file: Optional[str] = "config.yaml",
    ) -> None:

        self.opcua.init(opcua_endpoint)
        if config_file:
            try:
                config: Dict = yaml.safe_load(open(config_file, "r"))
                modbus_config = config["modbus"]
                self.modbus.config(
                    byte_order=(
                        Endian.BIG
                        if modbus_config["byte_order"] == "b"
                        else Endian.LITTLE
                    ),
                    word_order=(
                        Endian.BIG
                        if modbus_config["word_order"] == "b"
                        else Endian.LITTLE
                    ),
                )
                if "variables" in config.keys():
                    for variable in config["variables"]:
                        self.add_variable(SimVariable(**variable))
            except FileNotFoundError as e:
                logger.warning(f"Config file not found, {e}")
            except yaml.YAMLError as e:
                logger.warning(f"Invalid config file, {e}")

        self.modbus.init()

        @event(at=0, till=0, label="Start Modbus Server")
        async def start_modbus_server():
            logger.info("Starting Modbus server...")
            await StartAsyncTcpServer(
                context=self.modbus.server_context,
                identity=self.modbus.identity,
                address=(modbus_address, modbus_port),
            )

        @event(at=0, till=0, label="Start OPC UA Server")
        async def start_opcua_server() -> NoReturn:
            if security_policy:
                self.opcua.server.set_security_policy(security_policy)
            else:
                self.opcua.server.set_security_policy(
                    security_policy=[ua.SecurityPolicyType.NoSecurity]
                )
            if private_key and certificate:
                await self.opcua.server.load_private_key(path_or_content=private_key)
                await self.opcua.server.load_certificate(path_or_content=certificate)
            logger.info("Starting OPC UA server...")
            await self.opcua.server.start()

    def start(self) -> None:
        Akatosh.logger.setLevel(level=logging.INFO)
        Mundus.enable_realtime()
        asyncio.run(main=Mundus.simulate(till=inf))

    def add_variable(self, variable: SimVariable) -> None:
        """
        add_variable Creates a variable in the Modbus server and registers it in the OPC UA server.

        The variable is created in the Modbus server and registered in the OPC UA server. The variable is then added to the list of variables in the PLC and a synchronization event is created to keep the OPC UA variable in sync with the Modbus variable.

        Args:
            variable (SimVariable): the variable to be added.

        Raises:
            ValueError: raised when the value type is invalid for the variable type, or when the register size is invalid for holding and input registers.
        """
        # check if the OPC UA namespace exists
        # Each modbus slave has its own namespace and a root node with the slave id as qualified name
        namespace = f"http://sdics.com/ModBus/slave/{variable.modbus_slave}"
        if namespace not in self.opcua.namespaces.keys():
            self.opcua.register_namespace(namespace)
            self.opcua.register_node(
                qualified_name=f"{variable.modbus_slave}", namespace=namespace
            )

        # check if the modbus slave exists
        if variable.modbus_slave not in self.modbus.slaves.keys():
            # create the modbus slave if not exists
            self.modbus.create_slave(variable.modbus_slave)

        if variable.type == "c":
            if isinstance(variable.value, bool):
                self.modbus.create_coil(
                    variable.modbus_slave, variable.address, variable.value
                )

                self.opcua.register_variable(
                    variable.qualified_name,
                    True,
                    variable.value,
                    self.opcua.nodes[str(variable.modbus_slave)],
                )

                @event(
                    at=0,
                    till=inf,
                    label=f"Sync Coil {variable.qualified_name}",
                    priority=1,
                )
                async def sync_coil():
                    value: bool = await self.opcua.variables[
                        variable.qualified_name
                    ].read_value()
                    self.modbus.write_coil(
                        variable.modbus_slave, variable.address, value
                    )

            else:
                raise ValueError("Invalid value type for Modbus coil.")
        elif variable.type == "d":
            if isinstance(variable.value, bool):
                self.modbus.create_discrete_input(
                    variable.modbus_slave, variable.address, variable.value
                )

                self.opcua.register_variable(
                    variable.qualified_name,
                    False,
                    variable.value,
                    self.opcua.nodes[str(variable.modbus_slave)],
                )

                @event(
                    at=0,
                    till=inf,
                    label=f"Sync Discrete Input {variable.qualified_name}",
                    priority=1,
                )
                async def sync_discrete_input():
                    value: bool = await self.opcua.variables[
                        variable.qualified_name
                    ].read_value()

                    self.modbus.write_discrete_input(
                        variable.modbus_slave, variable.address, value
                    )

            else:
                raise ValueError("Invalid value type for Modbus discrete input.")
        elif variable.type == "h":
            if isinstance(variable.value, int) or isinstance(variable.value, float):
                if variable.register_size not in [16, 32, 64]:
                    raise ValueError(
                        "Invalid register size for Modbus holding register."
                    )
                self.modbus.create_holding_register(
                    variable.modbus_slave,
                    variable.address,
                    variable.value,
                    variable.register_size,
                )

                self.opcua.register_variable(
                    variable.qualified_name,
                    True,
                    variable.value,
                    self.opcua.nodes[str(variable.modbus_slave)],
                )

                @event(
                    at=0,
                    till=inf,
                    label=f"Sync Holding Register {variable.qualified_name}",
                    priority=1,
                )
                async def sync_holding_register():
                    value = await self.opcua.variables[
                        variable.qualified_name
                    ].read_value()
                    self.modbus.write_holding_register(
                        variable.modbus_slave, variable.address, value
                    )

            else:
                raise ValueError("Invalid value type for Modbus holding register.")
        elif variable.type == "i":
            if isinstance(variable.value, int) or isinstance(variable.value, float):
                if variable.register_size not in [16, 32, 64]:
                    raise ValueError("Invalid register size for Modbus input register.")
                self.modbus.create_input_register(
                    variable.modbus_slave,
                    variable.address,
                    variable.value,
                    variable.register_size,
                )

                self.opcua.register_variable(
                    variable.qualified_name,
                    False,
                    variable.value,
                    self.opcua.nodes[str(variable.modbus_slave)],
                )

                @event(
                    at=0,
                    till=inf,
                    label=f"Sync Input Register {variable.qualified_name}",
                    priority=1,
                )
                async def sync_input_register():
                    value = await self.opcua.variables[
                        variable.qualified_name
                    ].read_value()
                    self.modbus.write_input_register(
                        variable.modbus_slave, variable.address, value
                    )

            else:
                raise ValueError("Invalid value type for Modbus input register.")

        self.variables.append(variable)

    async def read_variable(self, qualified_name: str):
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
        variable = next(
            (var for var in self.variables if var.qualified_name == qualified_name),
            None,
        )
        if variable is None:
            raise RuntimeError("Variable not found.")
        return await self.opcua.variables[qualified_name].read_value()

    async def write_variable(self, qualified_name: str, value: int | float | bool):
        """
        write_variable Writes a value to a variable.

        The value is written to the Modbus server.

        Args:
            qualified_name (str): the qualified name of the variable to be written.
            value (int | float | bool): the value to be written.

        Raises:
            ValueError: raised if the variable is not found, or if the value type is invalid for the variable type.
        """
        variable = next(
            (var for var in self.variables if var.qualified_name == qualified_name),
            None,
        )
        if variable is None:
            raise RuntimeError("Variable not found.")
        if isinstance(variable.value, bool):
            value = bool(value)
        elif isinstance(variable.value, int):
            value = int(value)
        elif isinstance(variable.value, float):
            value = float(value)
        await self.opcua.variables[qualified_name].write_value(value)


simPLC = SDPLC()
