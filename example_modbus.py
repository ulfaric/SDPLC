import logging
from sdplc.modbus.server import modbusServer

# Enable debug logging for pymodbus
logging.basicConfig()
logging.getLogger('pymodbus').setLevel(logging.DEBUG)

modbusServer.create_slave(1)

# Create coils
for i in range(0, 10):
    modbusServer.create_coil(1, i, False)

# Create discrete inputs
for i in range(0, 10):
    modbusServer.create_discrete_input(1, i, False)

# Create holding registers
for i in range(0, 10):
    modbusServer.create_holding_register(1, i, 0, 16)

# Create input registers
for i in range(0, 10):
    modbusServer.create_input_register(1, i, 0, 16)

modbusServer.start()