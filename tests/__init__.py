from unittest import TestCase
from pymodbus.client import ModbusUdpClient

client = ModbusUdpClient("localhost", 1502)


resp = client.read_input_registers(0, 4)
print(resp.registers)
client.close()