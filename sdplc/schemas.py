from typing import Literal, Optional, List

from pydantic import BaseModel, field_validator, model_validator
from asyncua import ua

from sdplc import modbus
from .modbus.schemas import (
    ModBusIPConfig,
    ModBusSerialConfig,
)
from .opcua.schemas import OPCUAConfig


class ModBusRegConfig(BaseModel):
    slave: int = 1
    address: int = 0
    type: Literal["c", "d", "h", "i"] = "c"
    register_size: Literal[16, 32, 64] = 16


class OPCUANodeConfig(BaseModel):
    namespace: str = "root"
    node_qualified_name: str = "root"


class Node(BaseModel):
    qualified_name: str
    value: int | float | bool
    parents: Optional[List["Node"]] = []
    children: Optional[List["Node"]] = []
    # Modbus
    modbus: Optional[ModBusRegConfig] = None
    # OPCUA
    opcua: Optional[OPCUANodeConfig] = None

    @model_validator(mode="after")
    def check_modbus_type(self):
        if self.modbus:
            if self.modbus.type == "c" and not isinstance(self.value, bool):
                raise ValueError("Coil must have a boolean value.")
            if self.modbus.type == "d" and not isinstance(self.value, bool):
                raise ValueError("Discrete input must have a boolean value.")
            if self.modbus.type == "h" and not isinstance(self.value, (int, float)):
                raise ValueError(
                    "Holding register must have an integer or float value."
                )
            if self.modbus.type == "i" and not isinstance(self.value, (int, float)):
                raise ValueError("Input register must have an integer or float value.")
        return self


class Config(BaseModel):
    server: Optional[Literal["OPCUA", "ModBus"]] = None
    client: Optional[Literal["OPCUA", "ModBus"]] = None
    modbus_client_config: Optional[ModBusIPConfig | ModBusSerialConfig] = None
    modbus_server_config: Optional[ModBusIPConfig] = None
    opcua_client_config: Optional[OPCUAConfig] = None
    opcua_server_Config: Optional[OPCUAConfig] = None
    nodes: Optional[List[Node]] = None

    @model_validator(mode="after")
    def check_interfaces(self):
        if self.server == "ModBus" and self.modbus_server_config is None:
            raise ValueError("ModBus server config is required.")
        if self.server == "OPCUA" and self.opcua_server_Config is None:
            raise ValueError("OPCUA server config is required.")
        if self.client == "ModBus" and self.modbus_client_config is None:
            raise ValueError("ModBus client config is required.")
        if self.client == "OPCUA" and self.opcua_client_config is None:
            raise ValueError("OPCUA client config is required.")
        if self.client == self.server:
            raise ValueError("Server and client cannot be the same interface.")
        return self
