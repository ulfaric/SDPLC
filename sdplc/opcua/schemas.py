from typing import List, Optional
from pydantic import BaseModel
from asyncua import ua

class OPCUAConfig(BaseModel):
    url: str
    username: Optional[str] = None
    password: Optional[str] = None
    private_key: Optional[str] = None
    certificate: Optional[str] = None
    security_policy: Optional[List[int]] = [0]
