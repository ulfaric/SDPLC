import socket
from math import inf

import uvicorn
from Akatosh.event import event
from Akatosh.universe import Mundus
from FasterAPI.app import app
from asyncua import ua
from sdplc import logger
from sdplc.sdplc import simPLC
from sdplc.router import sim_plc_router
from FasterAPI.cert import generate_key_and_csr, generate_root_ca, sign_certificate

app.include_router(sim_plc_router)

time = 0
@event(at=0, step=1, till=inf, label="Tank Level Sensor", priority=2)
async def tank_level_sensor():
    current_tank_level = await simPLC.read_node("Tank Level")
    variable = [
        variable for variable in simPLC.nodes if variable.qualified_name == "Tank Level"
    ][0]
    logger.info(f"Tank Level Sensor: {current_tank_level}")


@event(at=0, till=inf, label="Tank Level Simulation", priority=2)
async def sim_tank_level():
    global time
    eclpsed_time = Mundus.time - time
    inlet = await simPLC.read_node("Inlet Valve")
    outlet = await simPLC.read_node("Outlet Valve")
    current_tank_level = await simPLC.read_node("Tank Level")
    if inlet is True:
        current_tank_level += 10 * eclpsed_time
    if outlet is True:
        current_tank_level -= 5 * eclpsed_time
    await simPLC.write_node("Tank Level", current_tank_level)
    time = Mundus.time

if __name__ == "__main__":
    simPLC.init(
        config_file="./example_plc.yaml",
    )
    uvicorn.run("FasterAPI.app:app", host="0.0.0.0", port=8080)
