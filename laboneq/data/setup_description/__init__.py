# Copyright 2020 Zurich Instruments AG
# SPDX-License-Identifier: Apache-2.0


# __init__.py of 'setup_description' package - autogenerated, do not edit
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


#
# Enums
#
class IODirection(Enum):
    IN = auto()
    OUT = auto()

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


class IOSignalType(Enum):
    DIO = auto()
    I = auto()
    IQ = auto()
    LO = auto()
    Q = auto()
    RF = auto()
    SINGLE = auto()
    ZSYNC = auto()

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


class PortMode(Enum):
    LF = auto()
    RF = auto()

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


class ReferenceClockSource(Enum):
    EXTERNAL = auto()
    INTERNAL = auto()

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


class DeviceType(Enum):
    HDAWG = auto()
    NonQC = auto()
    PQSC = auto()
    SHFQA = auto()
    SHFSG = auto()
    UHFQA = auto()
    SHFQC = auto()

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


class PhysicalChannelType(Enum):
    IQ_CHANNEL = auto()
    RF_CHANNEL = auto()

    def __repr__(self):
        return f"{self.__class__.__name__}.{self.name}"


#
# Data Classes
#


@dataclass
class LogicalSignal:
    uid: str = None
    name: str = None
    path: str = None
    direction: IODirection = None


@dataclass
class PhysicalChannel:
    uid: str = None
    type: PhysicalChannelType = None


@dataclass
class Connection:
    physical_channel: PhysicalChannel = None
    logical_signal: LogicalSignal = None


@dataclass
class Port:
    path: str = None
    physical_channel: Optional[PhysicalChannel] = None


@dataclass
class Server:
    uid: str = None
    api_level: int = None
    host: str = None
    leader_uid: str = None
    port: Any = None


@dataclass
class Instrument:
    uid: str = None
    interface: str = None
    ports: List[Port] = field(default_factory=list)
    physical_channels: List[PhysicalChannel] = field(default_factory=list)
    connections: List[Connection] = field(default_factory=list)
    address: str = None
    device_type: DeviceType = None
    server: Server = None


@dataclass
class LogicalSignalGroup:
    uid: str = None
    logical_signals: Dict[str, LogicalSignal] = field(default_factory=dict)


@dataclass
class QuantumElement:
    uid: str = None
    signals: List[LogicalSignal] = field(default_factory=list)
    parameters: List = field(default_factory=list)


@dataclass
class SetupInternalConnection:
    from_instrument: Instrument = None
    from_port: Port = None
    to_instrument: Instrument = None


@dataclass
class PhysicalChannelToLogicalSignalMapping:
    physical_channel: PhysicalChannel = None
    logical_signal: LogicalSignal = None


@dataclass
class Qubit(QuantumElement):
    pass


@dataclass
class Setup:
    uid: str = None
    servers: Dict[str, Server] = field(default_factory=dict)
    instruments: List[Instrument] = field(default_factory=list)
    logical_signal_groups: Dict[str, LogicalSignalGroup] = field(default_factory=dict)
    setup_internal_connections: List[SetupInternalConnection] = field(
        default_factory=list
    )
