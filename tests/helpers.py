"""Shared builders for the ndx-tank-metadata tests."""

from datetime import datetime, timezone

from ndx_tank_metadata import LabMetaDataExtension, MazeExtension, RigExtension
from pynwb import NWBHDF5IO, NWBFile

SESSION_START = datetime(2026, 8, 7, 12, 3, 23, tzinfo=timezone.utc)
SESSION_END = datetime(2026, 8, 7, 12, 33, 5, 250000, tzinfo=timezone.utc)

RIG = dict(
    name="rig",
    rig_type="miniVR",
    simulationMode=False,
    hasDAQ=True,
    hasSyncComm=False,
    minIterationDT=0.01,
    arduinoPort="COM5",
    sensorDotsPerRev=[1967.6, 1967.6, 1967.6, 1967.6],
    ballCircumference=63.8,
    toroidXFormP1=0.5193,
    toroidXFormP2=0.5171,
    colorAdjustment=[0.0, 0.4, 0.5],
    soundAdjustment=0.2,
    nidaqDevice=1,
    nidaqPort=1,
    nidaqLines=[0, 11],
    syncClockChannel=5,
    syncDataChannel=6,
    rewardChannel=0,
    rewardSize=0.004,
    rewardDuration=0.05,
    laserChannel=1,
    rightPuffChannel=2,
    leftPuffChannel=3,
)


def make_lab_metadata(rig=None, mazes=None, **overrides):
    if mazes is None:
        mazes = MazeExtension(name="mazes", description="mazes")
        mazes.add_row(world=1, lStart=5.0)
    kwargs = dict(
        name="LabMetaData",
        experiment_name="test",
        world_file_name="test",
        protocol_name="test",
        stimulus_bank_path="test",
        commit_id="test",
        location="test",
        num_trials=0,
        session_end_time=SESSION_END,
        rig=rig if rig is not None else RigExtension(**RIG),
        mazes=mazes,
    )
    kwargs.update(overrides)
    return LabMetaDataExtension(**kwargs)


def write_nwb(path, lab_metadata):
    nwbfile = NWBFile("description", "id", SESSION_START)
    nwbfile.add_lab_meta_data(lab_metadata)
    with NWBHDF5IO(str(path), "w") as io:
        io.write(nwbfile)
    return path
