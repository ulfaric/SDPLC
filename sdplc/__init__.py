
import logging
from typing import Dict

import colorlog
from Akatosh import logger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import \
    OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
import yaml

# config = yaml.safe_load(open("config.yaml"))
# try:
#     otlp_exporter = OTLPSpanExporter(
#         endpoint=config["trace"]["endpoint"],
#         insecure=True,
#     )

#     trace_provider = TracerProvider(
#         resource=Resource(attributes={"service.name": "Sim PLC"}),
#     )
#     trace_provider.add_span_processor(SimpleSpanProcessor(otlp_exporter))
#     trace.set_tracer_provider(trace_provider)
#     tracer: trace.Tracer = trace.get_tracer("Sim PLC")
# except:
#     tracer = None # type: ignore

# set up logging
logger: logging.Logger = logging.getLogger("Sim PLC")
# Define log colors
cformat = "%(log_color)s%(levelname)s:  %(message)s"
colors: Dict[str, str] = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red,bg_white",
}
# Set up stream handler
stream_handler = logging.StreamHandler()
stream_formatter = colorlog.ColoredFormatter(fmt=cformat, log_colors=colors)
stream_handler.setFormatter(fmt=stream_formatter)
stream_handler.setLevel(level=logging.DEBUG)
logger.addHandler(hdlr=stream_handler)
# Set up file handler
file_handler = logging.FileHandler(filename="backend.log")
file_formatter = logging.Formatter(
    fmt="%(asctime)s - %(levelname)s - %(message)s"
)
file_handler.setFormatter(fmt=file_formatter)
file_handler.setLevel(level=logging.ERROR)
logger.addHandler(hdlr=file_handler)
logger.setLevel(level=logging.DEBUG)
