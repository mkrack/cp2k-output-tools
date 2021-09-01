import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

import regex as re

from .common import Level
from .scf import match_scf
from .warnings import Message, match_messages

GEO_OPT_RE = re.compile(
    r"""
^\ \*+\n
\ \*{3} \s+ STARTING\ GEOMETRY\ OPTIMIZATION .+\n
\ \*{3} \s+ (?P<type>\S+) \s+ \*{3}\n
\ \*+\n
""",
    re.VERBOSE | re.MULTILINE,
)

GEO_OPT_STEP_RE = re.compile(
    r"""
^\ \-+\n
\ OPTIMIZATION\ STEP: \s+ (?P<stepnr>\d+)\n
\ \-+
""",
    re.VERBOSE | re.MULTILINE,
)

GEO_OPT_END_RE = re.compile(
    r"""
^(
\ \*{3} \s+ (?P<msg>MAXIMUM\ NUMBER .+?)\s+\*{3}\n
\ \*{3} \s+ EXITING\ GEOMETRY\ OPTIMIZATION .+\n
|
\ \*+\n
\ \*{3} \s+ (?P<msg>GEOMETRY\ OPTIMIZATION\ COMPLETED) .+\n
\ \*+\n
)
""",
    re.VERBOSE | re.MULTILINE,
)


@dataclass
class GeometryOptimization(Level):
    converged: bool


@dataclass
class GeometryOptimizationStep(Level):
    messages: List[Message]


def match_geo_opt(content: str, start: int = 0, end: int = sys.maxsize) -> Optional[Tuple[GeometryOptimization, Tuple[int, int]]]:
    start_match = GEO_OPT_RE.search(content, start, end)

    if not start_match:
        return None, (start, end)

    step_starts = [start_match.span()[1] + 1]
    step_ends = []

    for match in GEO_OPT_STEP_RE.finditer(content, start, end):
        step_end, step_start = match.span()  # the previous step ends where the next one starts

        step_starts.append(step_start)
        step_ends.append(step_end)

    stop_match = GEO_OPT_END_RE.search(content, start, end)
    converged = True
    if stop_match:
        step_ends.append(stop_match.span()[0])
        if "MAXIMUM NUMBER" in stop_match["msg"]:
            converged = False
    else:
        step_ends.append(end)
        converged = False

    steps = []
    for start, end in zip(step_starts, step_ends):
        sublevels = []

        scf, _ = match_scf(content, start, end)
        if scf:
            sublevels.append(scf)
        else:
            print("NO SCF FOUND in this", content[start:end])

        steps.append(GeometryOptimizationStep(messages=list(match_messages(content, start, end)), sublevels=sublevels))

    return GeometryOptimization(converged=converged, sublevels=steps), (start_match.span()[0], step_ends[-1])
