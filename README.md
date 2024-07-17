# SDPLC

SDPLC is a python library that is able to simulate a Modbus server, OPC UA server and a HTTPS server at the same time.

The Modbus and OPC UA server is compatable with standard clients and most SCADA systems. You could use SDPLC as a simulated PLC for developping and testing.

The HTTPS server allows RESTful API calls to retrive the available variables/registers, as well as read and write operations.

Addtionally, you can use the "Akatosh" library (pre-bundled) to create logic that mimic a real PLC that has been programmed.

Thanks "asyncua" and "pymodbus" for the implementation of OPC UA and Modbus protocols.

## Examples

The following example shows how to run three servers at the same time, and with a simulation of a tank plus blender system. Note that, Akatosh in real-time mode does not have a pre-defined time step, the simulated object will update as fast as possible which is only limited by the CPU speed. Thus, although the input/output valve is set with a integer as flow rate, the tank level will always be a float number.

This example also includes the certifcate creation for OPC UA server, which is optional if you choose not to use any security policy.

```python
import socket
from math import inf

import uvicorn
from Akatosh.event import event
from Akatosh.universe import Mundus
from FasterAPI.app import app
from asyncua import ua
from sdplc import logger
from sdplc.plc import simPLC
from sdplc.router import sim_plc_router
from FasterAPI.cert import generate_key_and_csr, generate_root_ca, sign_certificate

app.include_router(sim_plc_router)

time = 0


ca, ca_crt = generate_root_ca(
    common_name=socket.gethostname(),
    subject_alternative_names=[socket.gethostname()],
    directory="./",
)
server_key, server_csr = generate_key_and_csr(
    common_name=socket.gethostname(),
    san_dns_names=[socket.gethostname()],
    san_uris=["uri:ulfaric:SDPLC"],
    directory="./",
)
sign_certificate(csr=server_csr, issuer_key=ca, issuer_cert=ca_crt, directory="./")


@event(at=0, till=inf, label="Valve Control", priority=2)
async def inlet_control():
    current_tank_level = await simPLC.read_variable("Tank Level")
    if current_tank_level <= 0:
        inlet_state = await simPLC.read_variable("Inlet Valve")
        if inlet_state == False:
            await simPLC.write_variable("Inlet Valve", True)
            await simPLC.write_variable("Outlet Valve", False)
            logger.info(
                "Tank level reached lower threshold, closing outlet valve and opening inlet valve"
            )

    if current_tank_level >= 50 and current_tank_level < 100:
        inlet_state = await simPLC.read_variable("Inlet Valve")
        outlet_state = await simPLC.read_variable("Outlet Valve")
        if outlet_state == False:
            await simPLC.write_variable("Outlet Valve", True)
            logger.info("Tank level reached high threshold, opening both valves")
        if inlet_state == False:
            await simPLC.write_variable("Inlet Valve", True)
            logger.info("Tank level reached high threshold, opening both valves")

    if current_tank_level >= 150:
        inlet_state = await simPLC.read_variable("Inlet Valve")
        if inlet_state == True:
            await simPLC.write_variable("Inlet Valve", False)
            await simPLC.write_variable("Outlet Valve", True)
            logger.info(
                "Tank level reached critical threshold, closing inlet valve and opening outlet valve"
            )


@event(at=0, step=1, till=inf, label="Tank Level Sensor", priority=2)
async def tank_level_sensor():
    current_tank_level = await simPLC.read_variable("Tank Level")
    variable = [
        variable
        for variable in simPLC.variables
        if variable.qualified_name == "Tank Level"
    ][0]
    logger.info(f"Tank Level Sensor: {current_tank_level}")


@event(at=0, till=inf, label="Tank Level Simulation", priority=2)
async def sim_tank_level():
    global time
    eclpsed_time = Mundus.time - time
    inlet = await simPLC.read_variable("Inlet Valve")
    outlet = await simPLC.read_variable("Outlet Valve")
    current_tank_level = await simPLC.read_variable("Tank Level")
    if inlet is True:
        current_tank_level += 10 * eclpsed_time
    if outlet is True:
        current_tank_level -= 5 * eclpsed_time
    await simPLC.write_variable("Tank Level", current_tank_level)
    time = Mundus.time


@event(at=0, till=inf, label="Blender", priority=2)
async def blender():
    current_tank_level = await simPLC.read_variable("Tank Level")
    if current_tank_level >= 100:
        await simPLC.write_variable("Blender", True)
    else:
        await simPLC.write_variable("Blender", False)


if __name__ == "__main__":
    simPLC.init(
        security_policy=[ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt],
        config_file="./example_config.yaml",
    )
    uvicorn.run("FasterAPI.app:app", host="0.0.0.0", port=8080)
```

```yaml
modbus:
  byte_order: "big"
  word_order: "big"


variables:
  - qualified_name: "Inlet Valve"
    value: false
    modbus_slave: 0
    address: 0
    type: "c"

  - qualified_name: "Outlet Valve"
    value: true
    modbus_slave: 0
    address: 1
    type: "c"

  - qualified_name: "Tank Level"
    value: 0.0
    modbus_slave: 0
    address: 0
    type: "i"
    register_size: 64

  - qualified_name: "Blender"
    value: false
    modbus_slave: 0
    address: 2
    type: "c"
```

### Modbus

You can also just simulate a Modbus server. In this mode, you will have to add registers manually.

```python
from sdplc.modbus import modbus

modbus.create_slave(0)

for i in range(0, 10):
    modbus.create_coil(0, i, False)

for i in range(0, 10):
    modbus.create_discrete_input(0, i, False)

modbus.create_holding_register(0, 0, 0, 64)
modbus.create_input_register(0, 0, 1000, 64)

modbus.start()
```

### OPC UA

You can also just simulate a OPC UA server. You will also need to manually create namespace, node and variables.

```python
from sdplc.opcua import opcua

opcua.init()

namespace = "http://example.org"
opcua.register_namespace(namespace)
node = opcua.register_node("Tank", namespace)
opcua.register_variable("Tank Level", node=node, writeable=True, value=0)
opcua.register_variable("Tank Temperature", node_qualified_name="Tank", writeable=True, value=0)

opcua.start()
```
