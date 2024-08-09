from typing import Literal, Optional, List

from pydantic import BaseModel, field_validator, model_validator
from asyncua import ua
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
    north: Optional[List[Literal["OPCUA", "ModBus"]]] = ["OPCUA", "ModBus"]
    south: Optional[List[Literal["OPCUA", "ModBus"]]] = None
    modbus: Optional[ModBusIPConfig | ModBusSerialConfig] = None
    opcua: Optional[OPCUAConfig] = None
    nodes: Optional[List[Node]] = None

    @model_validator(mode="after")
    def check_interfaces(self):
        if not self.north and not self.south:
            raise ValueError("At least one interface must be enabled")

        if (
            self.north
            and self.south
            and "OPCUA" in self.north
            and "OPCUA" in self.south
        ):
            raise ValueError("OPCUA cannot be enabled on both interfaces")

        if (
            self.north
            and self.south
            and "ModBus" in self.north
            and "ModBus" in self.south
        ):
            raise ValueError("ModBus cannot be enabled on both interfaces")

        if self.north and "OPCUA" in self.north and not self.opcua:
            raise ValueError("OPCUA configuration is missing for north interface")

        if self.south and "OPCUA" in self.south and not self.opcua:
            raise ValueError("OPCUA configuration is missing for south interface")

        if self.north and "ModBus" in self.north and not self.modbus:
            raise ValueError("ModBus configuration is missing for north interface")

        if self.south and "ModBus" in self.south and not self.modbus:
            raise ValueError("ModBus configuration is missing for south interface")

        if self.nodes and not self.north:
            raise ValueError("Nodes can not be defined without any north interface.")

        if (
            self.north
            and "ModBus" in self.north
            and not isinstance(self.modbus, ModBusIPConfig)
        ):
            raise ValueError("ModBus server configuration is not supported for north")

        return self
