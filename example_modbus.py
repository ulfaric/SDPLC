from sdplc.modbus.server import modbusServer

modbusServer.create_slave(0)

for i in range(0, 10):
    modbusServer.create_coil(0, i, False)

for i in range(0, 10):
    modbusServer.create_discrete_input(0, i, False)

modbusServer.create_holding_register(0, 0, 0, 64)
modbusServer.create_input_register(0, 0, 1000, 64)

modbusServer.start()
