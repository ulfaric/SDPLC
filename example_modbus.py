from sdplc.modbus import modbus

modbus.create_slave(0)

for i in range(0, 10):
    modbus.create_coil(0, i, False)

for i in range(0, 10):
    modbus.create_discrete_input(0, i, False)

modbus.create_holding_register(0, 0, 0, 64)
modbus.create_input_register(0, 0, 1000, 64)

modbus.start()
