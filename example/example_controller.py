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
    current_tank_level = await simPLC.read_node("Tank Level")
    if current_tank_level <= 0:
        inlet_state = await simPLC.read_node("Inlet Valve")
        if inlet_state == False:
            await simPLC.write_node("Inlet Valve", True)
            await simPLC.write_node("Outlet Valve", False)
            logger.info(
                "Tank level reached lower threshold, closing outlet valve and opening inlet valve"
            )

    if current_tank_level >= 50 and current_tank_level < 100:
        inlet_state = await simPLC.read_node("Inlet Valve")
        outlet_state = await simPLC.read_node("Outlet Valve")
        if outlet_state == False:
            await simPLC.write_node("Outlet Valve", True)
            logger.info("Tank level reached high threshold, opening both valves")
        if inlet_state == False:
            await simPLC.write_node("Inlet Valve", True)
            logger.info("Tank level reached high threshold, opening both valves")

    if current_tank_level >= 150:
        inlet_state = await simPLC.read_node("Inlet Valve")
        if inlet_state == True:
            await simPLC.write_node("Inlet Valve", False)
            await simPLC.write_node("Outlet Valve", True)
            logger.info(
                "Tank level reached critical threshold, closing inlet valve and opening outlet valve"
            )


@event(at=0, step=1, till=inf, label="Tank Level Sensor", priority=2)
async def tank_level_sensor():
    current_tank_level = await simPLC.read_node("Tank Level")
    variable = [
        variable for variable in simPLC.nodes if variable.qualified_name == "Tank Level"
    ][0]
    logger.info(f"Tank Level Sensor: {current_tank_level}")


@event(at=0, till=inf, label="Blender", priority=2)
async def blender():
    current_tank_level = await simPLC.read_node("Tank Level")
    if current_tank_level >= 100:
        await simPLC.write_node("Blender", True)
    else:
        await simPLC.write_node("Blender", False)


if __name__ == "__main__":
    simPLC.init(
        config_file="./example_controller.yaml",
    )
    uvicorn.run("FasterAPI.app:app", host="0.0.0.0", port=8088)
