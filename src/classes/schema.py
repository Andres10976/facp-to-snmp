from pydantic import BaseModel

class SNMPConfig(BaseModel):
    community: str
    port: int
    trap_destination: str
    trap_port: int

class GPIOConfig(BaseModel):
    alarm_pin: int
    supervision_pin: int
    trouble_pin: int
    debounce_time: int

class OIDConfig(BaseModel):
    alarm: str
    supervision: str
    trouble: str
    event: str

class SerialConfig(BaseModel):
    port: str
    baudrate: int
    bytesize: int
    parity: str
    stopbits: int
    timeout: float

class Config(BaseModel):
    snmp: SNMPConfig
    gpio: GPIOConfig
    oids: OIDConfig
    serial: SerialConfig