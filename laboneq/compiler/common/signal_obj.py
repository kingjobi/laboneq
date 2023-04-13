# Copyright 2022 Zurich Instruments AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List, Optional

from laboneq.core.types.enums.mixer_type import MixerType

if TYPE_CHECKING:
    from laboneq.compiler.common.awg_info import AWGInfo
    from laboneq.compiler.common.device_type import DeviceType


@dataclass(init=True, repr=True, order=True)
class SignalObj:
    """A collection of a signal's properties relevant for code generation. The delay
    fields are in seconds and their meaning is as follows:
    - start_delay: the delay from the trigger to the start of the sequence (lead time),
      realized as initial playZeros; includes lead time and precompensation
    - delay_signal: user-defined additional delay, realized by adding to the initial
      playZeros; rounded to the sequencer grid (sample_multiple)
    - total_delay: the sum of the above two fields, plus delays generated during code
      generation, e.g., relative delay between a play and acquire pulse
    - on_device_delay: delay on the device, realized by delay nodes and independent
      from the sequencer, generated during code generation, e.g., relative delay between
      a play and acquire pulse; in addition to potential port delays specified via the
      calibration
    - port_delay: port delay specified via the calibration; realized via the device node
      in addition to potential on-device delays
    """

    id: str
    sampling_rate: float
    start_delay: float
    delay_signal: float
    signal_type: str
    device_id: str
    device_type: DeviceType
    oscillator_frequency: float = None  # for software modulation only
    pulses: List = field(default_factory=list)
    channels: List = field(default_factory=list)
    awg: AWGInfo = None
    total_delay: float = None
    on_device_delay: float = 0
    port_delay: float = 0
    mixer_type: Optional[MixerType] = None
    hw_oscillator: Optional[str] = None
    is_qc: Optional[bool] = None
