# ndx-tank-metadata

NWB LabMetaData extension for [Tank lab](https://pni.princeton.edu/faculty/david-tank).

# Install

```
$ pip install ndx-tank-metadata
```

# Usage

This extension is built for extending the LabMetaData schema with custom fields requested for the
conversion of Virmen metadata. The extension is built into the Tank lab conversion
pipeline ([tank-lab-to-nwb](https://github.com/catalystneuro/tank-lab-to-nwb)) and is not necessary
to be installed separately. Alternatively, it can be used from a python script as demonstrated below.

## Modifying

The schema is generated from a field registry, `src/pynwb/ndx_tank_metadata/virmen_fields.yaml`: one entry per
ViRMEn log field, with its NWB destination, name, dtype, canonical shape, unit, description and known codes. Entries
with `in_spec: true` become columns or attributes.

To change the schema, edit the registry, bump the version in `pyproject.toml`, then run
`python src/spec/create_extension_spec.py` to regenerate `spec/`. Don't edit the YAML in `spec/` by hand: a test
compares it with the generator's output.

## Types

| Type | Parent | Contents |
|---|---|---|
| `LabMetaDataExtension` | `LabMetaData` | Session metadata, plus the groups below |
| `RigExtension` | `LabMetaData` | Rig parameters |
| `AnimalSettings` | `LabMetaData` | Training settings of the animal |
| `MazeExtension` | `DynamicTable` | One row per maze |
| `StimulusPairs` | `DynamicTable` | One row per (block, stimulus pair) in the PWM task |
| `VirmenSettings` | `DynamicTable` | Key/value settings whose meaning is unknown or defined by each experiment |
| `VirmenTrials` | `TimeIntervals` | Use as `nwbfile.trials` |
| `VirmenEpochs` | `TimeIntervals` | Use as `nwbfile.epochs` |

Every column is optional, so a session that doesn't log a field simply leaves it out. Pass a typed array to keep a
declared dtype: for variable-length columns, give a typed `VectorData` and an explicit `VectorIndex`.

## Example

```python
from datetime import datetime

import numpy as np
from hdmf.common import VectorData, VectorIndex
from pynwb import NWBHDF5IO, NWBFile

from ndx_tank_metadata import LabMetaDataExtension, MazeExtension, RigExtension, VirmenTrials

nwbfile = NWBFile('description', 'id', datetime.now().astimezone())

rig = RigExtension(
    name='rig',
    rig_type='miniVR',
    simulationMode=False,
    hasDAQ=True,
    minIterationDT=0.01,
    sensorDotsPerRev=[1967.6, 1967.6, 1967.6, 1967.6],
    colorAdjustment=[0., 0.4, 0.5],
    nidaqLines=[0, 11],
    rewardChannel=0,
)

mazes = MazeExtension(name='mazes', description='description of the mazes')
mazes.add_row(world=1, lStart=5.0, lCue=45.0, lMemory=10.0, maxBias=1.0, warmupMaze=[])
mazes.add_row(world=2, lStart=5.0, lCue=45.0, lMemory=10.0, maxBias=0.2, warmupMaze=[1.0, 2.0])

lab_metadata = LabMetaDataExtension(
    name='LabMetaData',
    experiment_name='test',
    world_file_name='test',
    protocol_name='test',
    location='test',
    num_trials=2,
    session_end_time=datetime.now().astimezone(),  # timezone-aware datetime
    rig=rig,
    mazes=mazes,
)
nwbfile.add_lab_meta_data(lab_metadata)

# Cue positions vary per trial: two on the left in trial 0, none in trial 1.
cue_positions = VectorData(name='cuePos_left', description='cue positions', data=np.array([10.5, 20.5], dtype='float32'))
nwbfile.trials = VirmenTrials(
    name='trials',
    description='trials',
    columns=[
        VectorData(name='start_time', description='start', data=np.array([0.0, 5.0])),
        VectorData(name='stop_time', description='stop', data=np.array([4.0, 9.0])),
        VectorData(name='iCueEntry', description='cue entry', data=np.array([62, 46], dtype='int32')),
        cue_positions,
        VectorIndex(name='cuePos_left_index', data=np.array([2, 2], dtype='uint32'), target=cue_positions),
    ],
)

with NWBHDF5IO('test_labmetadata.nwb', 'w') as io:
    io.write(nwbfile)
```
