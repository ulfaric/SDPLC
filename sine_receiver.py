import logging
from math import inf
from datetime import datetime, timezone
import uvicorn
from Akatosh.event import event
from FasterAPI.app import app
from sdplc import logger
from sdplc.sdplc import simPLC
from sdplc.router import sim_plc_router

app.include_router(sim_plc_router)
logger.setLevel(logging.INFO)


@event(at=0, step=0.1, till=inf, label="Recording", priority=2)
async def recording():
    recording = await simPLC.read_node("Recording")
    if recording is True:
        amplitude = await simPLC.read_node("SineWave")
        current_time = datetime.now(timezone.utc).isoformat()
        with open("sine_wave_data_receiver.txt", "a") as file:
            file.write(f"{current_time},{amplitude}\n")


@event(at=0, step=1, till=inf, label="Sine Wave Sensor", priority=2)
async def sine_wave_reading():
    amplitude = await simPLC.read_node("SineWave")
    logger.info(f"Sine Wave: {amplitude}")


if __name__ == "__main__":
    simPLC.init(
        config_file="./sine_receiver.yaml",
    )
    uvicorn.run("FasterAPI.app:app", host="0.0.0.0", port=8080)
