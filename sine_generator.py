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

time = 0


@event(at=0, step=0.1,till=inf, label="Recording", priority=2)
async def recording():
    recording = await simPLC.read_node("Recording")
    if recording is False:
        await simPLC.write_node("Recording", True)
    else:
        with open("sine_wave_data_generator.txt", "a") as file:
            amplitude = await simPLC.read_node("SineWave")
            current_time = datetime.now(timezone.utc).isoformat()
            file.write(f"{current_time},{amplitude}\n")


@event(at=0, step=0.02, till=inf, label="Sine Wave Sensor", priority=2)
async def sine_wave_reading():
    recording = await simPLC.read_node("Recording")
    if recording is True:
        amplitude = sin(2 * pi * 1 * Mundus.time)
        await simPLC.write_node("SineWave", amplitude)
        logger.info(f"Sine Wave: {amplitude}")


if __name__ == "__main__":
    simPLC.init(
        config_file="./sine_generator.yaml",
    )
    uvicorn.run("FasterAPI.app:app", host="0.0.0.0", port=8088)
