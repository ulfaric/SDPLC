import re
from typing import Literal, Optional
from pydantic import BaseModel, field_validator, model_validator


class ModBusIPConfig(BaseModel):
    type: Literal["tcp", "udp", "tls"] = "tcp"
    address: str
    port: int
    certificate: Optional[str] = None
    key: Optional[str] = None
    ca: Optional[str] = None
    byte_order: Literal["big", "little"] = "big"
    word_order: Literal["big", "little"] = "big"

    @model_validator(mode="after")
    def check_tls(self):
        if self.type == "tls" and not self.certificate:
            raise ValueError("TLS certificate is missing")
        if self.type == "tls" and not self.key:
            raise ValueError("TLS key is missing")
        return self


class ModBusSerialConfig(BaseModel):
    port: str
    baudrate: int
    bytesize: int = 8
    parity: Literal["N", "E", "O", "S", "M"] = "N"
    stopbits: int = 1
    byte_order: Literal["big", "little"] = "big"
    word_order: Literal["big", "little"] = "big"
