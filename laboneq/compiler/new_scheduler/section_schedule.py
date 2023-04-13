# Copyright 2022 Zurich Instruments AG
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Iterator, List, Set, Tuple

from attrs import define, field

from laboneq.compiler.common.compiler_settings import CompilerSettings
from laboneq.compiler.common.event_type import EventType
from laboneq.compiler.new_scheduler.interval_schedule import IntervalSchedule
from laboneq.compiler.new_scheduler.pulse_schedule import PrecompClearSchedule
from laboneq.compiler.new_scheduler.utils import ceil_to_grid, floor_to_grid
from laboneq.core.exceptions.laboneq_exception import LabOneQException

if TYPE_CHECKING:
    from laboneq.compiler.new_scheduler.schedule_data import ScheduleData


@define(kw_only=True, slots=True)
class SectionSchedule(IntervalSchedule):
    right_aligned: bool

    #: The id of the section
    section: str

    #: Tuple of section IDs that must be scheduled before this interval.
    play_after: List[str] = field(factory=list)

    #: Trigger info: signal, bit
    trigger_output: Set[Tuple[str, int]] = field(factory=set)

    def adjust_length(self, new_length: int):
        """Adjust length to the new value.

        The alignment is respected. No check is done to verify if the new length is
        long enough to fit the contents."""
        assert self.length is not None
        if self.length == new_length:
            return
        assert self.children_start is not None
        new_length = ceil_to_grid(new_length, self.grid)
        delta = new_length - self.length
        self.length = new_length
        if self.right_aligned:
            self.children_start = [start + delta for start in self.children_start]

    def adjust_grid(self, new_grid: int):
        """Adjust grid to the new value. If the new grid is not commensurate with the
        length, the length is also increased. Right-aligned sections have their children
        moved to the right when adjusting the length."""
        assert self.children_start is not None
        new_length = ceil_to_grid(self.length, new_grid)
        if self.length == new_length:
            return
        delta = new_length - self.length
        self.length = new_length
        if self.right_aligned:
            self.children_start = [start + delta for start in self.children_start]

    def _arrange_left_aligned(
        self,
        schedule_data: ScheduleData,
        absolute_start: int,
        children_index_by_name: Dict[str, int],
        start_may_change: bool,
    ):
        assert self.children_start is not None
        current_signal_start = {}
        for i, c in enumerate(self.children):
            start = max(
                (current_signal_start.setdefault(s, 0) for s in c.signals), default=0
            )
            pa_names = getattr(c, "play_after", None)
            if pa_names:
                pa_section = getattr(c, "section")
                for pa_name in pa_names:
                    if pa_name not in children_index_by_name:
                        raise LabOneQException(
                            f"Section '{pa_section}' should play after section '{pa_name}',"
                            f"but it is not defined at the same level."
                        )
                    pa_index = children_index_by_name[pa_name]
                    if pa_index >= i:
                        raise LabOneQException(
                            f"Section '{pa_section}' should play after section '{pa_name}',"
                            f"but it is actually defined earlier."
                        )
                    pa = self.children[pa_index]
                    assert pa.length is not None
                    assert len(self.children_start) > pa_index
                    start = max(start, self.children_start[pa_index] + pa.length)

            elif isinstance(c, PrecompClearSchedule):
                # find the referenced pulse
                try:
                    start = next(
                        self.children_start[j]
                        for j, other_child in enumerate(self.children[:i])
                        if other_child is c.pulse
                    )
                except StopIteration:
                    raise RuntimeError(
                        "The precompensation clear refers to a pulse that could not be "
                        "found."
                    )
            start = ceil_to_grid(start, c.grid)
            start = (
                c.calculate_timing(
                    schedule_data, absolute_start + start, start_may_change
                )
                - absolute_start
            )
            self.children_start[i] = start
            for s in c.signals:
                current_signal_start[s] = start + c.length

    def _arrange_right_aligned(
        self,
        schedule_data: ScheduleData,
        absolute_start: int,
        children_index_by_name: Dict[str, int],
    ):
        assert self.children_start is not None
        current_signal_end = {}
        play_before: Dict[str, List[str]] = {}
        for c in self.children:
            pa_names = getattr(c, "play_after", None)
            if pa_names:
                pa_section = getattr(c, "section")
                for pa_name in pa_names:
                    play_before.setdefault(pa_name, []).append(pa_section)
        for i, c in reversed(list(enumerate(self.children))):
            offset = (
                c.calculate_timing(schedule_data, absolute_start, True) - absolute_start
            )
            assert offset == 0
            assert c.length is not None
            start = (
                min((current_signal_end.setdefault(s, 0) for s in c.signals), default=0)
                - c.length
            )
            pb_section = getattr(c, "section", None)
            if pb_section is not None:
                for pb_name in play_before.get(pb_section, []):
                    if pb_name not in children_index_by_name:
                        raise LabOneQException(
                            f"Section '{pb_name}' should play after section '{pb_section}',"
                            f"but it is not defined at the same level."
                        )
                    pb_index = children_index_by_name[pb_name]
                    if pb_index <= i:
                        raise LabOneQException(
                            f"Section '{pb_name}' should play after section '{pb_section}', "
                            f"but is actually defined earlier."
                        )
                    start = min(start, self.children_start[pb_index] - c.length)
            elif isinstance(c, PrecompClearSchedule):
                raise LabOneQException(
                    "Cannot reset the precompensation filter inside a right-aligned section."
                )

            start = floor_to_grid(start, c.grid)
            self.children_start[i] = start
            for s in c.signals:
                current_signal_end[s] = start

        section_start = floor_to_grid(
            min((v for v in self.children_start if v is not None), default=0), self.grid
        )

        self.children_start = [start - section_start for start in self.children_start]

    def _calculate_timing(
        self, schedule_data: ScheduleData, start: int, start_may_change
    ) -> int:
        children_index_by_name = {
            child.section: i
            for i, child in enumerate(self.children)
            if isinstance(child, SectionSchedule)
        }
        if not self.right_aligned:
            self._arrange_left_aligned(
                schedule_data, start, children_index_by_name, start_may_change
            )
        else:
            self._arrange_right_aligned(schedule_data, start, children_index_by_name)
        self._calculate_length(schedule_data)
        return start

    def _calculate_length(self, schedule_data: ScheduleData):
        assert self.children_start is not None
        if len(self.children):
            length = ceil_to_grid(
                max(
                    (
                        start + (c.length or 0)
                        for (c, start) in zip(self.children, self.children_start)
                    ),
                    default=0,
                ),
                self.grid,
            )
        else:
            length = 0

        if self.length is not None:
            # force length
            force_length = ceil_to_grid(self.length, self.grid)
            if force_length < length:
                raise LabOneQException(
                    f"Content of section '{self.section}' "
                    f"({length*schedule_data.TINYSAMPLE*1e6:.3e} us) does not fit into "
                    f"the requested fixed section length ({force_length*schedule_data.TINYSAMPLE*1e6:.3e} us)"
                )
            self.length = length
            self.adjust_length(force_length)
        else:
            self.length = length

    def generate_event_list(
        self,
        start: int,
        max_events: int,
        id_tracker: Iterator[int],
        expand_loops,
        settings: CompilerSettings,
    ) -> List[Dict]:
        assert self.length is not None
        assert self.absolute_start is not None

        # We'll wrap the child events in the section start and end events
        max_events -= 2

        trigger_set_events = []
        trigger_clear_events = []
        for trigger_signal, bit in self.trigger_output:
            if max_events < 2:
                break
            max_events -= 2
            event = {
                "event_type": EventType.DIGITAL_SIGNAL_STATE_CHANGE,
                "section_name": self.section,
                "bit": bit,
                "signal": trigger_signal,
            }

            trigger_set_events.append({**event, "change": "SET", "time": start})
            trigger_clear_events.append(
                {
                    **event,
                    "change": "CLEAR",
                    "time": start + self.length,
                }
            )

        children_events = self.children_events(
            start, max_events, settings, id_tracker, expand_loops
        )

        start_id = next(id_tracker)
        d = {"section_name": self.section, "chain_element_id": start_id}
        if self.trigger_output is not None and len(self.trigger_output):
            d["trigger_output"] = [
                {"signal_id": signal} for signal, _ in self.trigger_output
            ]

        return [
            {
                "event_type": EventType.SECTION_START,
                "time": start,
                "id": start_id,
                **d,
            },
            *trigger_set_events,
            *[e for l in children_events for e in l],
            *trigger_clear_events,
            {
                "event_type": EventType.SECTION_END,
                "time": start + self.length,
                "id": next(id_tracker),
                **d,
            },
        ]

    def children_events(
        self,
        start: int,
        max_events: int,
        settings: CompilerSettings,
        id_tracker: Iterator[int],
        expand_loops,
        subsection_events=True,
    ) -> List[List[Dict]]:
        assert self.children_start is not None

        if subsection_events:
            # take into account that we'll wrap with subsection events
            max_events -= 2 * len(self.children)

        children_events = super().children_events(
            start, max_events, settings, id_tracker, expand_loops
        )

        # if children_events was cut because max_events was exceeded, pad with empty
        # lists. This is necessary because the PSV requires the subsection events to be
        # present.
        # todo: investigate if this is a bug in the PSV.
        for i in range(len(self.children) - len(children_events)):
            children_events.append([])

        if subsection_events:
            # Wrap child sections in SUBSECTION_START & SUBSECTION_END.
            start_id = next(id_tracker)
            d = {"section_name": self.section, "chain_element_id": start_id}
            for i, child in enumerate(self.children):
                if isinstance(child, SectionSchedule):
                    assert child.length is not None
                    children_events[i] = [
                        {
                            "event_type": EventType.SUBSECTION_START,
                            "time": self.children_start[i] + start,
                            "subsection_name": child.section,
                            "id": start_id,
                            **d,
                        },
                        *children_events[i],
                        {
                            "event_type": EventType.SUBSECTION_END,
                            "time": self.children_start[i] + child.length + start,
                            "subsection_name": child.section,
                            "id": next(id_tracker),
                            **d,
                        },
                    ]

        return children_events

    def __hash__(self):
        return super().__hash__()
