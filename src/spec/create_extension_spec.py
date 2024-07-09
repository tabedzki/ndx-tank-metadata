import os
from pynwb.spec import NWBNamespaceBuilder, NWBGroupSpec, export_spec


def main():
    ns_builder = NWBNamespaceBuilder(
        doc='type for storing metadata for Tank lab',
        name='ndx-tank-metadata',
        version='0.2.0',
        author=['Szonja Weigl', 'Luiz Tauffer', 'Ben Dichter', 'Christian Tabedzki'],
        contact=['ben.dichter@gmail.com', 'ct5868@princeton.edu']
    )

    ns_builder.include_type('LabMetaData', namespace='core')
    ns_builder.include_type('DynamicTable', namespace='core')

    LabMetaDataExtension = NWBGroupSpec(
        doc='type for storing metadata for Brody and Tank labs',
        neurodata_type_def='LabMetaDataExtension',
        neurodata_type_inc='LabMetaData',
    )

    LabMetaDataExtension.add_attribute(
        name='experiment_name',
        doc='name of experiment run',
        dtype='text',
    )

    LabMetaDataExtension.add_attribute(
        name='world_file_name',
        doc='name of world file run',
        dtype='text',
    )

    LabMetaDataExtension.add_attribute(
        name='protocol_name',
        doc='name of protocol run',
        dtype='text',
    )

    LabMetaDataExtension.add_attribute(
        name='stimulus_bank_path',
        doc='path of stimulus bank file',
        dtype='text',
    )

    LabMetaDataExtension.add_attribute(
        name='commit_id',
        doc='Commit id for session run',
        dtype='text',
    )

    LabMetaDataExtension.add_attribute(
        name='location',
        doc='Name of rig where session was run',
        dtype='text',
    )

    LabMetaDataExtension.add_attribute(
        name='session_performance',
        doc='Performance of correct responses in %',
        dtype='float',
        required=False
    )

    LabMetaDataExtension.add_attribute(
        name='session_end_time',
        doc='Datetime when session ended',
        dtype='text',  # temporary solution until datetime is fixed
    )

    LabMetaDataExtension.add_attribute(
        name='num_trials',
        doc='Number of trials during the session',
        dtype='int',
    )

    RigExtension = NWBGroupSpec(
        doc='type for storing rig information',
        neurodata_type_def='RigExtension',
        neurodata_type_inc='LabMetaData',
    )

    rig_attr = [

                ('rig', 'text', 'miniVR or normalVR (projection is changed based on rig type)'),
                ('simulationMode', 'int', 'true to run in simulation mode with human input via keyboard'),
                ('hasDAQ', 'int', 'false for testing on laptop'),
                ('hasSyncComm', 'int', 'true if digital communications should be used for synchronization (ScanImage)'),
                ('minIterationDT', 'float', 'Minimum expected ViRMEn frame rate in seconds'),
                ('arduinoPort', 'text', 'Arduino port as seen in the Windows Device Manager'),
                ('sensorDotsPerRev', 'float', 'Sensor dots per ball revolution, obtained using the calibrateBall script'),
                ('ballCircumference', 'float', 'in cm'),
                ('toroidXFormP1', 'float', 'p1 parameter (slope) from poly1 fit of toroidal screen transformation'),
                ('toroidXFormP2', 'float', 'p2 parameter (offset) from poly1 fit of toroidal screen transformation'),
                ('colorAdjustment', 'float', '[R; G; B] scale factor for projector display'),
                ('soundAdjustment', 'float', 'Scale factor for sound volume'),
                ('nidaqDevice', 'int', 'NI-DAQ device identifier'),
                ('nidaqPort', 'int', 'NI-DAQ port number'),
                ('nidaqLines', 'int', 'NI-DAQ lines for the specified port'),
                ('syncClockChannel', 'int', 'NI-DAQ digital line for I2C clock signal'),
                ('syncDataChannel', 'int', 'NI-DAQ digital line for I2C data signal'),
                ('rewardChannel', 'int', 'NI-DAQ digital line for turning on/off the solenoid valve'),
                ('rewardSize', 'float', 'in mL'),
                ('rewardDuration', 'float', 'Valve opening duration (in seconds) for 4uL reward'),
                ('laserChannel', 'int', 'NI-DAQ digital line for turning on/off the laser'),
                ('rightPuffChannel', 'int', 'NI-DAQ digital line for left air puff solenoid'),
                ('leftPuffChannel', 'int', 'NI-DAQ digital line for right air puff solenoid'),
                ('webcam_name', 'text', 'Webcam name')

                ]


    for (attr, datatype, description) in rig_attr:
        if attr in ['sensorDotsPerRev', 'colorAdjustment', 'nidaqLines']:
            RigExtension.add_attribute(
                name=attr,
                doc=description,
                dtype=datatype,
                shape=(None,),
                required=False
            )
        else:
            RigExtension.add_attribute(
                name=attr,
                doc=description,
                dtype=datatype,
                required=False
            )


    LabMetaDataExtension.add_group(
        name='rig',
        neurodata_type_inc='RigExtension',
        doc='type for storing rig information',
    )

    LabMetaDataExtension.add_group(
        name='mazes',
        neurodata_type_inc='MazeExtension',
        doc='type for storing maze information',
    )

    MazeExtension = NWBGroupSpec(
        doc='type for storing maze information',
        neurodata_type_def='MazeExtension',
        neurodata_type_inc='DynamicTable',
    )

    maze_attr = [

                ( "StartCycle",	"PWM and spatfreq. The spatial frequency of the first stimulus shown to the mouse.",	"int",),
                ( "EndCycle",	"PWM. The spatial frequency of the second stimulus shown to the mouse.",	"int",),
                ( "stimulusTable",	"PWM. Cell array containing the various (StartCycle,EndCycle) pairs that can be shown, their probabilities, their hitrates, the times they've been shown, etc.",	"object",), #array<object>
                ( "rule",	"PWM. Specifies what the mouse should do to receive reward. Can be 'StartCycle < EndCycle Left' or 'StartCycle < EndCycle Right'",	"utf-8",),
                ( "baseCycles",	"PWM. The base set of spatial frequencies from which StartCycle and EndCycle can be drawn.",	"int",), #"array<int>",
                ( "trialNum",	"PWM. The trial number (not reliable, bugged).",	"int",),
                ( "hitHistory",	"PWM. Boolean vector tracking whether the mouse got the trial correct or not.",	"bool",), #"array<bool>"
                ( "classHistory",	"PWM. Vector tracking which (StartCycle,EndCycle) stimulus pair was shown to the mouse, with each value being a row index into stimulusTable.",	"int",), #array<int>
                ( "multibiasBeta",	"PWM. Scalar value indicating the strength of the multibias.",	"float",),
                ( "multibiasTau",	"PWM. Scalar value indicating the history dependence of the multibias.",	"float",),
                ( "pairNum",	"PWM. Integer value indicating which stimulus pair was shown, is a row index into stimulusTable.",	"int",),
                ( "wallGuide",	"PWM. Boolean, whether wallGuides were active or not on this trial.",	"bool",),
                ( "alpha_plus",	"PWM. Scalar, how much to multiply step_size by when moving the moon beacon trigger forward.",	"float",),
                ( "alpha_minus",	"PWM. Scalar, how much to multiply step_size by when moving the moon beacon trigger back.",	"float",),
                ( "moonBeaconEnabled",	"PWM. Boolean, whether the moon beacon is enabled or not.",	"bool",),
                ( "moonBeaconPos",	"PWM. Scalar [cm], current position of the moon beacon trigger relative to the moonBeaconTrigger.",	"float",),
                ( "moonBeaconTrigger",	"PWM. String indicating the trigger point for the moon. Can be 'Sa' or 'Sb'.",	"utf-8",),
                ( "step_size",	"PWM. Scalar [cm], how much to move the moon beacon triggerpoint on each trial.",	"float",),
                ( "lsrON",	"pro/anti. whether the laser is on for a given trial, 0=laser off, 1=laser on",	"int",),
                ( "moonDistHint",	"pro/anti. distance from start at which moon beacon appears",	"float",),
                ( "forcedChoice",	"spatfreq. whether a trial is a forced choice L-maze environment, 0=T-maze, 1=L-maze",	"int",),

                ]


    for (attr, description, datatype) in maze_attr:
        if attr in ['baseCycles', 'baseCycles', 'classHistory']:
            MazeExtension.add_attribute(
                name=attr,
                doc=description,
                dtype=datatype,
                shape=(None,),
                required=False
            )
        else:
            MazeExtension.add_attribute(
                name=attr,
                doc=description,
                dtype=datatype,
                required=False
            )


    # export the extension to yaml files in the spec folder
    output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'spec'))
    export_spec(ns_builder, [LabMetaDataExtension, RigExtension, MazeExtension], output_dir)


if __name__ == "__main__":
    main()
