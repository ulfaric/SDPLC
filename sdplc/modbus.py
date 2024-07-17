import asyncio
import logging
import math
from dataclasses import dataclass
from turtle import st
from typing import Dict, List, Literal, Optional

import Akatosh
from Akatosh.event import event
from Akatosh.universe import Mundus
from pymodbus.constants import Endian
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusServerContext,
    ModbusSlaveContext,
)
from pymodbus.device import ModbusDeviceIdentification
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
from pymodbus.server import StartAsyncTcpServer

from . import logger


@dataclass
class ModBusCoil:
    slave: int
    address: int
    value: bool = False


@dataclass
class ModBusDiscreteInput:
    slave: int
    address: int
    value: bool = False


@dataclass
class ModBusHoldingRegister:
    slave: int
    address: int
    value: int | float = 0
    size: Literal[16, 32, 64] = 16
    type: Literal["int", "float"] = "float"


@dataclass
class ModBusInputRegister:
    slave: int
    address: int
    value: int | float = 0
    size: Literal[16, 32, 64] = 16
    type: Literal["int", "float"] = "float"


class ModBusSlave:
    def __init__(self, id: int) -> None:
        """
        __init__ create a ModBusSlave object.

        Create a ModBusSlave object with the given id. This object is not equivalent to a ModbusSlaveContext object. It stores the registers configuration and initialise the ModbusSlaveContext object.

        Args:
            id (int): the id of the slave.
        """
        self.id = id
        self.coils: List[ModBusCoil] = list()
        self.coils_memory = [0 for _ in range(65534)]
        self.coils_memory_occupancy = [False for _ in range(65534)]
        self.discrete_inputs: List[ModBusDiscreteInput] = list()
        self.discrete_inputs_memory = [0 for _ in range(65534)]
        self.discrete_inputs_memory_occupancy = [False for _ in range(65534)]
        self.holding_registers: List[ModBusHoldingRegister] = list()
        self.holding_registers_memory = [0 for _ in range(65534)]
        self.holding_registers_memory_occupancy = [False for _ in range(65534)]
        self.input_registers: List[ModBusInputRegister] = list()
        self.input_registers_memory = [0 for _ in range(65534)]
        self.input_registers_memory_occupancy = [False for _ in range(65534)]
        self.context: Optional[ModbusSlaveContext] = None

    def add_coil(self, address: int, value: bool = False):
        """
        add_coil Add a coil to the slave.

        The coil will be added in the ModBusSlaveContext object when the initialize method is called.

        Args:
            address (int): the address of the coil.
            value (bool, optional): the default value of the coil. Defaults to False.
        """
        if self.coils_memory_occupancy[address]:
            raise ValueError(f"Coil at address {address} is already occupied.")
        self.coils.append(ModBusCoil(slave=self.id, address=address, value=value))
        self.coils_memory[address] = value
        self.coils_memory_occupancy[address] = True
        logger.info(
            f"Added coil to slave {self.id} at address {address} with value {value}."
        )

    def add_discrete_input(self, address: int, value: bool = False):
        """
        add_discrete_input Add a discrete input to the slave.

        The discrete input will be added in the ModBusSlaveContext object when the initialize method is called.

        Args:
            address (int): the address of the discrete input.
            value (bool, optional): the default value of the discrete input. Defaults to False.
        """
        if self.discrete_inputs_memory_occupancy[address]:
            raise ValueError(
                f"Discrete input at address {address} is already occupied."
            )
        self.discrete_inputs.append(
            ModBusDiscreteInput(slave=self.id, address=address, value=value)
        )
        self.discrete_inputs_memory[address] = value
        self.discrete_inputs_memory_occupancy[address] = True
        logger.info(
            f"Added discrete input to slave {self.id} at address {address} with value {value}."
        )

    def add_holding_register(
        self, address: int, value: int | float = 0, size: Literal[16, 32, 64] = 16
    ):
        """
        add_holding_register Add a holding register to the slave.

        The holding register will be added in the ModBusSlaveContext object when the initialize method is called.

        Args:
            address (int): the address of the holding register.
            value (int | float, optional): the default value of the holding register. Defaults to 0.
            size (Literal[16, 32, 64], optional): the size of the holding register. Defaults to 16.
        """
        if any(self.holding_registers_memory_occupancy[address : address + size // 16]):
            raise ValueError(
                f"Holding register at address {address}:{address+size//16} is already occupied."
            )
        if isinstance(value, int):
            type = "int"
        elif isinstance(value, float):
            type = "float"
        self.holding_registers.append(
            ModBusHoldingRegister(
                slave=self.id, address=address, value=value, size=size, type=type
            )
        )
        bits = modbus.encoder(value, size)
        self.holding_registers_memory[address : address + size // 16] = bits
        self.holding_registers_memory_occupancy[address : address + size // 16] = [
            True for _ in range(size // 16)
        ]
        logger.info(
            f"Added holding register to slave {self.id} at address {address}:{address+size//16} with value {value} : {self.holding_registers_memory[address:address+size//16]}."
        )

    def add_input_register(
        self, address: int, value: int | float = 0, size: Literal[16, 32, 64] = 16
    ):
        """
        add_input_register Add a input register to the slave.

        The input register will be added in the ModBusSlaveContext object when the initialize method is called.

        Args:
            address (int): the address of the input register.
            value (int | float, optional): the default value of the input register. Defaults to 0.
            size (Literal[16, 32, 64], optional): the size of the input register. Defaults to 16.
        """
        if any(self.input_registers_memory_occupancy[address : address + size // 16]):
            raise ValueError(
                f"Input register at address {address}:{address+size//16} is already occupied."
            )
        if isinstance(value, int):
            type = "int"
        elif isinstance(value, float):
            type = "float"
        self.input_registers.append(
            ModBusInputRegister(
                slave=self.id, address=address, value=value, size=size, type=type
            )
        )
        bits = modbus.encoder(value, size)
        self.input_registers_memory[address : address + size // 16] = bits
        self.input_registers_memory_occupancy[address : address + size // 16] = [
            True for _ in range(size // 16)
        ]
        logger.info(
            f"Added input register to slave {self.id} at address {address}:{address+size//16} with value {value} : {self.input_registers_memory[address : address + size // 16]}."
        )

    def initialize(self):
        """
        initialize Initialize the ModBusSlaveContext object.

        This will create the ModBusSlaveContext object with the registers configuration. A full memory map is created and if no register at a given address is defined, the value is set to 0.

        Returns:
            ModbusSlaveContext: return the ModbusSlaveContext object.
        """
        c = ModbusSequentialDataBlock(0, self.coils_memory)
        d = ModbusSequentialDataBlock(0, self.discrete_inputs_memory)
        h = ModbusSequentialDataBlock(0, self.holding_registers_memory)
        i = ModbusSequentialDataBlock(0, self.input_registers_memory)
        self.context = ModbusSlaveContext(di=d, co=c, hr=h, ir=i, zero_mode=True)
        return self.context


class SimPLCModBus:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        """Create a simulated PLC based on Modbus."""
        self.slaves_context: Dict[int, ModbusSlaveContext] = {}
        self.server_context: ModbusServerContext | None = None  # type: ignore
        self.identity = ModbusDeviceIdentification()
        self.identity.VendorName = "SDPLC"
        self.identity.ProductCode = "SDPLC"
        self.identity.VendorUrl = "https://github.com/ulfaric/sdplc"
        self.identity.ProductName = "SDPLC"
        self.identity.ModelName = "SDPLC"
        self.identity.MajorMinorRevision = "1.0"
        self.slaves: Dict[int, ModBusSlave] = {}
        self.byte_order = Endian.BIG
        self.word_order = Endian.BIG

    def create_coil(self, slave: int, address: int, value: bool = False):
        """
        create_coil Create a coil in the slave.

        Create a coil in the slave with the given address and value. The coil will be added in the ModBusSlaveContext object when the initialize method is called.

        Args:
            slave (int): the id of the slave.
            address (int): the address of the coil.
            value (bool, optional): the default value of the coil. Defaults to False.
        """
        self.slaves[slave].add_coil(address, value)

    def read_coil(self, slave: int, address: int) -> bool:
        """
        read_coil read a coil in the slave.

        Read the value of the coil at the given address.

        Args:
            slave (int): the id of the slave.
            address (int): the address of the coil.

        Returns:
            bool: return the value of the coil.
        """
        register: ModbusSequentialDataBlock = self.slaves_context[slave].store["c"]
        bits = register.getValues(address, 1)
        return bits[0]

    def write_coil(self, slave: int, address: int, value: bool) -> bool:
        """
        write_coil Write a coil in the slave.

        Write the value of the coil at the given address.

        Args:
            slave (int): the id of the slave.
            address (int): the address of the coil.
            value (bool): the value to be written.

        Returns:
            bool: return the value of the coil to verify the write operation.
        """
        register: ModbusSequentialDataBlock = self.slaves_context[slave].store["c"]
        register.setValues(address, value)
        return register.getValues(address, 1)[0]

    def create_discrete_input(self, slave: int, address: int, value: bool = False):
        """
        create_discrete_input Create a discrete input in the slave.

        Create a discrete input in the slave with the given address and value. The discrete input will be added in the ModBusSlaveContext object when the initialize method is called.

        Args:
            slave (int): _description_
            address (int): _description_
            value (bool, optional): _description_. Defaults to False.
        """
        self.slaves[slave].add_discrete_input(address, value)

    def read_discrete_input(self, slave: int, address: int) -> bool:
        """
        read_discrete_input Read a discrete input in the slave.

        Read the value of the discrete input at the given address.

        Args:
            slave (int): the id of the slave.
            address (int): the address of the discrete input.

        Returns:
            bool: the value of the discrete input.
        """
        register: ModbusSequentialDataBlock = self.slaves_context[slave].store["d"]
        bits = register.getValues(address, 1)
        return bits[0]

    def write_discrete_input(self, slave: int, address: int, value: bool) -> bool:
        """
        write_discrete_input Write a discrete input in the slave.

        Write the value of the discrete input at the given address.

        Args:
            slave (int): the id of the slave.
            address (int): the address of the discrete input.
            value (bool): the value to be written.

        Returns:
            bool: the value of the discrete input to verify the write operation.
        """
        register: ModbusSequentialDataBlock = self.slaves_context[slave].store["d"]
        register.setValues(address, value)
        return register.getValues(address, 1)[0]

    def create_holding_register(
        self,
        slave: int,
        address: int,
        value: int | float = 0,
        size: Literal[16, 32, 64] = 16,
    ):
        """
        create_holding_register Create a holding register in the slave.

        Create a holding register in the slave with the given address, value, and size. The holding register will be added in the ModBusSlaveContext object when the initialize method is called.

        Args:
            slave (int): the id of the slave.
            address (int): the address of the holding register.
            value (int | float, optional): the default value of the holding register. Defaults to 0.
            size (Literal[16, 32, 64], optional): the size of the register. Defaults to 16.
        """
        self.slaves[slave].add_holding_register(address, value, size)

    def read_holding_register(self, slave: int, address: int) -> int | float:
        """
        read_holding_register Read a holding register in the slave.

        Read the value of the holding register at the given address.

        Args:
            slave (int): the id of the slave.
            address (int): the address of the holding register.

        Returns:
            int | float: the value of the holding register.
        """
        register: ModbusSequentialDataBlock = self.slaves_context[slave].store["h"]
        size = self.slaves[slave].holding_registers[address].size
        bits = register.getValues(address, size // 16)
        format = self.slaves[slave].holding_registers[address].type
        return modbus.decoder(bits, format)

    def write_holding_register(
        self, slave: int, address: int, value: int | float
    ) -> int | float:
        """
        write_holding_register Write a holding register in the slave.

        Write the value of the holding register at the given address.

        Args:
            slave (int): the id of the slave.
            address (int): the address of the holding register.
            value (int | float): the value to be written.

        Returns:
            int | float: the value of the holding register to verify the write operation.
        """
        register: ModbusSequentialDataBlock = self.slaves_context[slave].store["h"]
        size = self.slaves[slave].holding_registers[address].size
        type = self.slaves[slave].holding_registers[address].type
        bits = modbus.encoder(value, size)
        for i in range(size // 16):
            register.setValues(address + i, bits[i])
        return modbus.decoder(register.getValues(address, size // 16), type)

    def create_input_register(
        self,
        slave: int,
        address: int,
        value: int | float = 0,
        size: Literal[16, 32, 64] = 16,
    ):
        """
        create_input_register Create a input register in the slave.

        Create a input register in the slave with the given address, value, and size. The input register will be added in the ModBusSlaveContext object when the initialize method is called.

        Args:
            slave (int): the id of the slave.
            address (int): the address of the input register.
            value (int | float, optional): the default value of the input register. Defaults to 0.
            size (Literal[16, 32, 64], optional): the size of the input register. Defaults to 16.
        """
        self.slaves[slave].add_input_register(address, value, size)

    def read_input_register(self, slave: int, address: int) -> int | float:
        """
        read_input_register Read a input register in the slave.

        Read the value of the input register at the given address.

        Args:
            slave (int): the id of the slave.
            address (int): the address of the input register.

        Returns:
            int | float: the value of the input register.
        """
        register: ModbusSequentialDataBlock = self.slaves_context[slave].store["i"]
        size = self.slaves[slave].input_registers[address].size
        bits = register.getValues(address, size // 16)
        format = self.slaves[slave].input_registers[address].type
        return modbus.decoder(bits, format)

    def write_input_register(
        self, slave: int, address: int, value: int | float
    ) -> int | float:
        """
        write_input_register Write a input register in the slave.

        Write the value of the input register at the given address.

        Args:
            slave (int): the id of the slave.
            address (int): the address of the input register.
            value (int | float): the value to be written.

        Returns:
            int | float: the value of the input register to verify the write operation.
        """
        register: ModbusSequentialDataBlock = self.slaves_context[slave].store["i"]
        size = self.slaves[slave].input_registers[address].size
        type = self.slaves[slave].input_registers[address].type
        bits = modbus.encoder(value, size)
        for i in range(size // 16):
            register.setValues(address + i, bits[i])
        return modbus.decoder(register.getValues(address, size // 16), type)

    def create_slave(self, id: int):
        """
        create_slave Create a ModBus slave.

        Create a ModBus slave with the given id.

        Args:
            id (int): the id of the slave.
        """
        slave = ModBusSlave(id=id)
        self.slaves[id] = slave
        logger.info(f"Created ModBus slave {id}.")

    def config(self, byte_order: Endian, word_order: Endian):
        self.byte_order = byte_order
        self.word_order = word_order

    def init(self):
        """Create a server context with the given slaves."""
        for id, slave in self.slaves.items():
            self.slaves_context[id] = slave.initialize()
        self.server_context = ModbusServerContext(
            slaves=self.slaves_context, single=False
        )
        logger.info("Created ModBus server context.")
        return self.server_context

    def start(self, address: str = "0.0.0.0", port: int = 1502):
        """
        serve Initialize and start the Modbus server.

        This method initialize the server context and start the Modbus server at the given address and port. It is supported to run modbus server independently.

        Args:
            address (str): the address of the modbus server to be served on. This should be one of host machine IP address from its interface, or 0.0.0.0.
            port (int): the port of the modbus server to be served on.
        """
        self.init()

        @event(at=0, till=0, label="Start Modbus server", priority=0)
        async def start_modbus_server():
            await StartAsyncTcpServer(
                context=self.server_context,
                identity=self.identity,
                address=(address, port),
            )

        Akatosh.logger.setLevel(logging.INFO)
        Mundus.enable_realtime()
        asyncio.run(Mundus.simulate(math.inf))

    def encoder(self, value: int | float, size: Literal[16, 32, 64] = 16):
        builder = BinaryPayloadBuilder(
            byteorder=modbus.byte_order, wordorder=modbus.word_order
        )
        if isinstance(value, int):
            if size == 16:
                builder.add_16bit_int(value)
            elif size == 32:
                builder.add_32bit_int(value)
            elif size == 64:
                builder.add_64bit_int(value)
        elif isinstance(value, float):
            if size == 16:
                raise ValueError("16 bit float is not supported.")
            if size == 32:
                builder.add_32bit_float(value)
            elif size == 64:
                builder.add_64bit_float(value)
        return builder.to_registers()

    def decoder(
        self,
        bits: List[int],
        type: Literal["int", "float"] = "float",
    ):
        """
        decoder Decode the bits to int or float.

        Decode the bits to int or float based on the given size and format.

        Args:
            bits (List[int]): the bits to be decoded.
            size (Literal[16, 32, 64], optional): the length of the bits. Defaults to 16.
            format (Literal[&quot;int&quot;, &quot;float&quot;], optional): the type of the value. Defaults to "float".

        Returns:
            int | float: The decoded value.
        """
        decoder = BinaryPayloadDecoder.fromRegisters(
            bits, byteorder=modbus.byte_order, wordorder=modbus.word_order
        )
        if type == "float":
            if len(bits) * 8 == 16:
                raise ValueError("16 bit float is not supported.")
            elif len(bits) * 8 == 32:
                return decoder.decode_32bit_float()
            elif len(bits) * 8 == 64:
                return decoder.decode_64bit_float()
        if type == "int":
            if len(bits) * 8 == 16:
                return decoder.decode_16bit_int()
            elif len(bits) * 8 == 32:
                return decoder.decode_32bit_int()
            elif len(bits) * 8 == 64:
                return decoder.decode_64bit_int()
        raise ValueError(
            f"Invalid length of bits,  expected 16, 32 or 64, but got {len(bits)}."
        )


# Create a singleton instance of the SimPLCModBus class
modbus = SimPLCModBus()
