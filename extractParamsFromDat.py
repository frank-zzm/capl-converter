import os
import sys
from argparse import ArgumentParser

hilscriptdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'HilScripts')
sys.path.insert(0, hilscriptdir)

from hil.param.readers import set_parameters_from_dat
from hil.param.manager import ParameterData, ParameterManager

# parameter definitions taken from http://aes-build.eu.autoliv.int/job/Vision_ReleaseSmpc5R5Artifacts/74/artifact/artifacts/mcurelease/smpc5_B4-nonm/documentation/parameters.json/*view*/
# maps id to alv_type, NOTE: This alv_type must be a key in PARAMETERDATA_TYPE_FORMAT
NOT_READ_ONLY = False
INF = float('inf')

PARAMETER_DEFINITIONS = [
    ParameterData('PAR_hbaGeneral.lightControlMode', 'B7E1CFEE', 'U8', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.installationRollAngle', 'D83673C8', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.installationYawAngle', '048FF985', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.installationPitchAngle', '97E90262', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.afacCamPosY', 'EF007F51', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.afacCamPosX', '98074FC7', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.afacCamPosZ', '76092EEB', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.wheelBase', '24EFADE7', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.wheelRadius', 'A4C7B582', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.frontAxisToBumper', 'F4374B1C', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.afacHeadlampPosY', 'E8E5143B', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.afacHeadlampPosX', '9FE224AD', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.afacHeadlampPosZ', '71EC4581', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.viewAngleToHood', 'B0BFD809', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.vehicleWidth', 'DF4B49F1', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.frontAxisToGround', 'AD386045', 'float', -INF, INF, NOT_READ_ONLY),
    ParameterData('PAR_vehicleCoding.driveWheels', '55BC42BD', 'U8', -INF, INF, NOT_READ_ONLY)
]

DEFAULT_VALUES = {
    'B7E1CFEE': 4
}


class ParameterFilter:

    def __init__(self, parameter_ids):
        self.parameter_ids = parameter_ids

    def __str__(self):
        return 'ConversionParameterFilter ({})'.format(', '.join(self.parameter_ids))

    def accept(self, parameter: ParameterData):
        return parameter.param_id in self.parameter_ids


def extract(inputfile, outputfile):
    """
    Get parameters from a ADTF .dat file. The parameters searched for are the ones in wanted_ids.

    :param inputfile: .dat file with "ECU parameters" extension.
    :param outputfile: Text file where parameter id:s and values are written.
    :return: False if the ECU parameters extension does not exist, or in case of exception, otherwise True.
    """
    filter = ParameterFilter([p.param_id for p in PARAMETER_DEFINITIONS])
    parameter_manager = ParameterManager()
    for parameter in PARAMETER_DEFINITIONS:
        try:
            default_value = DEFAULT_VALUES[parameter.param_id]
            parameter.set_value(default_value, 'default')
            print('Setting default value {id} = {value}'.format(id=parameter.param_id, value=default_value))
        except KeyError:
            pass  # No default value defined

        parameter_manager.add_parameter(parameter)

    set_parameters_from_dat(parameter_manager, inputfile, param_filter=filter)
    parameter_manager.dump()
    parameter_manager.verify()
    write_to_file(parameter_manager, outputfile)


def write_to_file(parameter_manager, outputfile):
    with open(outputfile, "w") as out:
        out.write('/*@!Encoding:1252*/\n')
        out.write('variables\n')
        out.write('{\n')
        for name in parameter_manager.get_parameter_names():
            parameter = parameter_manager.get_parameter_by_name(name)
            out.write('  {type} {name} = {value};\n'.format(type='float',
                                                            name=parameter.name.replace('.', '_'),
                                                            value=parameter.value))
        out.write('}\n')


if __name__ == '__main__':
    parser = ArgumentParser(description='Parameter extraction tool')
    parser.add_argument('inputfile', type=str, help='input-file')
    parser.add_argument('outputfile', type=str, help='output-file')
    args = parser.parse_args()

    extract(args.inputfile, args.outputfile)
