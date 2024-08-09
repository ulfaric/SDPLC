from pymodbus.client import (
    AsyncModbusSerialClient,
    AsyncModbusTcpClient,
    AsyncModbusTlsClient,
    AsyncModbusUdpClient,
)
from .schemas import ModBusIPConfig, ModBusSerialConfig
import ssl


class SDPLCModBusClient:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:
        """
        __init__ Create a new ModBusClient instance.

        This is a wrapper around the pymodbus async clients with a configuration.
        """
        self._config: ModBusIPConfig | ModBusSerialConfig | None = None
        self._client: (
            AsyncModbusTcpClient
            | AsyncModbusSerialClient
            | AsyncModbusTlsClient
            | AsyncModbusUdpClient
            | None
        ) = None

    def config(self, config: ModBusIPConfig | ModBusSerialConfig) -> None:
        """
        config configures the ModBus client with the given configuration.

        This method must be called before calling connect.

        Args:
            config (ModBusTCPClientConfig | ModBusSerialClientConfig): the configuration to use.
        """
        self._config = config

    async def connect(self) -> None:
        """
        connect initializes the ModBus client connection.

        This method must be callled first before calling any read or write methods.

        Raises:
            ValueError: raised if the configuration is missing.
        """
        if isinstance(self._config, ModBusIPConfig):
            if self._config.type == "tcp":
                self._client = AsyncModbusTcpClient(
                    host=self._config.address,
                    port=self._config.port,
                )
            elif self._config.type == "udp":
                self._client = AsyncModbusUdpClient(
                    host=self._config.address,
                    port=self._config.port,
                )
            elif self._config.type == "tls":
                sslctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
                if self._config.certificate and self._config.key:
                    sslctx.load_cert_chain(self._config.certificate, self._config.key)
                else:
                    raise ValueError("TLS certificate and key are missing")
                if self._config.ca:
                    sslctx.load_verify_locations(self._config.ca)

                self._client = AsyncModbusTlsClient(
                    host=self._config.address,
                    port=self._config.port,
                    sslctx=sslctx,
                )
            else:
                raise ValueError("ModBus client type is not supported")
        elif isinstance(self._config, ModBusSerialConfig):
            self._client = AsyncModbusSerialClient(
                port=self._config.port,
                baudrate=self._config.baudrate,
                bytesize=self._config.bytesize,
                parity=self._config.parity,
                stopbits=self._config.stopbits,
            )
        else:
            raise ValueError("ModBus client configuration is missing")
        await self._client.connect()

    async def read_input_registers(self, address: int, count: int, slave: int):
        """
        read_input_registers a method to read input registers from a ModBus slave.

        This method reads input registers from a ModBus slave. It is wrapper around the pymodbus read_input_registers method.

        Args:
            address (int): the starting address to read from.
            count (int): the number of registers to read.
            slave (int): the slave id to read from.

        Raises:
            ValueError: the ModBus client is not initialized and connected.

        Returns:
            ModbusResponse: return the pymodbus response.
        """
        if not self._client:
            raise ValueError("ModBus client is not connected")
        return await self._client.read_input_registers(address, count, slave)

    async def read_holding_registers(self, address: int, count: int, slave: int):
        """
        read_holding_registers a method to read holding registers from a ModBus slave.

        This method reads holding registers from a ModBus slave. It is wrapper around the pymodbus read_holding_registers method.

        Args:
            address (int): the starting address to read from.
            count (int): the number of registers to read.
            slave (int): the slave id to read from.

        Raises:
            ValueError: the ModBus client is not initialized and connected.

        Returns:
            ModbusResponse: return the pymodbus response.
        """
        if not self._client:
            raise ValueError("ModBus client is not connected")
        return await self._client.read_holding_registers(address, count, slave)

    async def write_holding_registers(
        self, address: int, values: list[int], slave: int
    ):
        if not self._client:
            raise ValueError("ModBus client is not connected")
        return await self._client.write_registers(address, values, slave)

    async def read_coils(self, address: int, count: int, slave: int):
        """
        read_coils a method to read coils from a ModBus slave.

        This method reads coils from a ModBus slave. It is wrapper around the pymodbus read_coils method.

        Args:
            address (int): the starting address to read from.
            count (int): the number of coils to read.
            slave (int): the slave id to read from.

        Raises:
            ValueError: raised if the ModBus client is not connected.

        Returns:
            ModbusResponse: return the pymodbus response.
        """
        if not self._client:
            raise ValueError("ModBus client is not connected")
        return await self._client.read_coils(address, count, slave)

    async def write_coils(self, address: int, values: list[bool], slave: int):
        if not self._client:
            raise ValueError("ModBus client is not connected")
        return await self._client.write_coils(address, values, slave)

    async def write_coil(self, address: int, value: bool, slave: int):
        if not self._client:
            raise ValueError("ModBus client is not connected")
        return await self._client.write_coil(address, value, slave)

    async def read_discrete_inputs(self, address: int, count: int, slave: int):
        if not self._client:
            raise ValueError("ModBus client is not connected")
        return await self._client.read_discrete_inputs(address, count, slave)


modbusClient = SDPLCModBusClient()
