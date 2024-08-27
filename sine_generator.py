from math import inf, sin, pi
from datetime import datetime, timezone
import uvicorn
from Akatosh.event import event
from Akatosh.universe import Mundus
from FasterAPI.app import app
from sdplc import logger
from sdplc.sdplc import simPLC
from sdplc.router import sim_plc_router

app.include_router(sim_plc_router)


@event(at=0, till=0, once=True, label="Start", priority=2)
async def start_recording():
    await simPLC.write_node("Recording", True)


@event(at=0, step=0.1, till=30, label="Recording", priority=2)
async def recording():
    current_time = datetime.now(timezone.utc).isoformat()
    with open("sine_wave_data_generator.txt", "a") as file:
        amplitude = [
            node.value for node in simPLC.nodes if node.qualified_name == "SineWave"
        ][0]
        file.write(f"{current_time},{amplitude}\n")


@event(at=30, till=30, once=True, label="Stop", priority=3)
async def stop_recording():
    await simPLC.write_node("Recording", False)


@event(at=0, till=30, label="Sine Wave Generator", priority=2)
async def sine_wave_generator():
    amplitude = sin(2 * pi * 0.25 * Mundus.time)
    await simPLC.write_node("SineWave", amplitude)


@event(at=0, step=1, till=inf, label="Sine Wave Sensor", priority=2)
async def sine_wave_reading():
    amplitude = await simPLC.read_node("SineWave")
    logger.info(f"Sine Wave: {amplitude}")


if __name__ == "__main__":
    simPLC.init(
        config_file="./sine_generator.yaml",
    )
    uvicorn.run("FasterAPI.app:app", host="0.0.0.0", port=8088)
