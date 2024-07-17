from typing import Literal, Optional

from pydantic import BaseModel


class SimVariable(BaseModel):
    qualified_name: str
    value: int | float | bool
    modbus_slave: int
    address: int
    type: Literal["c", "d", "h", "i"]
    register_size: Optional[Literal[16, 32, 64]]=16
