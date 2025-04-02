import os

from hdmf.utils import docval, get_docval

from pynwb import load_namespaces, register_class
from pynwb.file import DynamicTable

try:
    from hdmf.utils import call_docval_func
except ImportError:
    pass


name = "ndx-tank-metadata"

spec_path = os.path.abspath(os.path.dirname(__file__))
ns_path = os.path.join(spec_path, "spec", f"{name}.namespace.yaml")

load_namespaces(ns_path)


@register_class("MazeExtension", name)
class MazeExtension(DynamicTable):
    """
    Table for storing maze information
    """

    mazes_attr = [
        "world",
        "lStart",
        "lCue",
        "lMemory",
        "cueDuration",
        "cueVisibleAt",
        "cueProbability",
        "cueDensityPerM",
        "antiFraction",
        "nCueSlots",
        "tri_turnHint",
        "color",
        "numTrials",
        "numTrialsPerMin",
        "criteriaNTrials",
        "warmupNTrials",
        "numSessions",
        "performance",
        "maxBias",
        "warmupMaze",
        "warmupPerform",
        "warmupBias",
        "warmupMotor",
        "easyBlock",
        "easyBlockNTrials",
        "numBlockTrials",
        "StartCycle",
        "EndCycle",
        "stimulusTable",
        "rule",
        "baseCycles",
        "trialNum",
        "hitHistory",
        "classHistory",
        "multibiasBeta",
        "multibiasTau",
        "pairNum",
        "wallGuide",
        "alpha_plus",
        "alpha_minus",
        "moonBeaconEnabled",
        "moonBeaconPos",
        "moonBeaconTrigger",
        "step_size",
        "lsrON",
        "moonDistHint",
        "forcedChoice",
        "blockPerform",
    ]

    __columns__ = tuple(
        {
            "name": attr,
            "description": "maze information",
            "required": False,
            "index": False,
            "table": False,
        }
        for attr in mazes_attr
    )

    @docval(
        {"name": "name", "type": str, "doc": "name of this MazeExtension"},  # required
        {"name": "description", "type": str, "doc": "Description of this DynamicTable"},
        *get_docval(DynamicTable.__init__, "id", "columns", "colnames"),
    )
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
