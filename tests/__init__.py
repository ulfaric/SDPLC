from unittest import TestCase
from pymodbus.client import ModbusTcpClient

client = ModbusTcpClient("localhost", 1502)


client.write_coil(1, value=True)

client.close()