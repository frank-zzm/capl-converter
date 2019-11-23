import logging
import os
import socket
import subprocess
import time
from argparse import ArgumentParser
from common.FileOperation  import *

from common.constants import LOG_FOLDER, PYTHON, CANOE_IMPORT_FOLDER, RUNNING_NAME, POST_PROCESS_IMPORT_FOLDER
from common.logger import init_logging

logger = logging.getLogger(__name__)

VERSION = "0.11"
SUCCESS = 0
FAIL = 1
import datetime


if __name__ == '__main__':

    parser = ArgumentParser(description='CAPL Converter')
    parser.add_argument('-V', '--version', action='version', version='%%(prog)s (version %s)' % VERSION)
    parser.add_argument('-l', '--log-path', default=None, type=str, help='Path to store log files')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--flc2-resim-2910', dest='FLC2', action='store_true', help='FLC2 Resim with 2910 conversion')
    group.add_argument('--dai-to-flc2', dest='DAI', action='store_true', help='DAI to FLC2 conversion')
    #
    # group .add_argument('--SVS-to-MVS',dest='Geea', action='store_true',help='svs to mvs conversion')
    group.add_argument('--E3U-to-MVS',dest= 'GEEA_E3U',action='store_true',help='E3U SVS2MVS conversion')
    group.add_argument('--E4-to-MVS',dest= 'GEEA_E4',action='store_true',help='E4 SVS2MVS conversion')
    group.add_argument('--core2E4-to-SVS', dest='GEEA_CORE2E3U', action='store_true', help='CORE 2 E4 SVS conversion')
    group.add_argument('--DAI2E4-to-SVS', dest='GEEA_DAI2E4', action='store_true', help='DAI 2 E4 SVS conversion')
    group.add_argument('--E3U2E4-to-SVS', dest='GEEA_E3U2E4', action='store_true', help='E3U 2 E4 SVS conversion')


    parser.add_argument('batchJobId', type=str, help='Job ID')
    parser.add_argument('fileList', type=str, help='Filelist to convert')
    parser.add_argument('resultFolder', type=str, help='Result folder')
    parser.add_argument('FlexRay_channel',type=str, help='Original Flexray channel')
    args = parser.parse_args()

    # Inputs
    batchJobId = args.batchJobId
    fileList = args.fileList
    resultFolder = args.resultFolder
    FlexRay_channel=args.FlexRay_channel

    # Initialize rotating log files
    logpath = args.log_path if args.log_path else "{}\{}".format(resultFolder, LOG_FOLDER)
    filename = "{host}.{name}.log".format(host=socket.gethostname(),
                                          name=os.path.splitext(os.path.basename(__file__))[0])
    filepath = os.path.abspath(os.path.join(logpath, filename))
    init_logging(log_file=filepath, max_file_size_mb=5, max_backup_count=10)

    logger.info("Version {}".format(VERSION))

    if args.FLC2:
        conversion_spec_argument = '--flc2-resim-2910'
    elif args.DAI:
        conversion_spec_argument = '--dai-to-flc2'
    elif args.GEEA_E3U:
        conversion_spec_argument = '--E3U-to-MVS'
    elif args.GEEA_E4:
        conversion_spec_argument = '--E4-to-MVS'
    elif args.GEEA_E3U2E4:
        conversion_spec_argument = '--E3U2E4-to-SVS'
    elif args.GEEA_CORE2E3U:
        conversion_spec_argument= '--core2E4-to-SVS'
    elif args.GEEA_DAI2E4:
        conversion_spec_argument='--DAI2E4-to-SVS'
    else:
        raise ValueError('No conversion specification selected!')

    print("start make log directory")
    cmdList = [PYTHON, "prepareForConversionTools.py", batchJobId, fileList, resultFolder,FlexRay_channel]
    ret = subprocess.call(cmdList)

    if ret != 0:
        logger.error("Error code {}: Program aborted!".format(ret))
        exit(FAIL)

    #
    # Start pre-conversion script
    #
    print("start pre-conversion,export 2 asc")
    canoeFolder = "{}\{}".format(resultFolder, CANOE_IMPORT_FOLDER)
    runningName = "{}\{}".format(canoeFolder, RUNNING_NAME)
    runningFP = open(runningName, "w")
    if runningFP is None:
        logger.error("Error: Failed to create file! Program aborted!")
        exit(FAIL)

    runningFP.close()

    logger.info("Start preProcessConversion.py")
    cmdList = [PYTHON, "./preProcessConversion.py", batchJobId, fileList, resultFolder, conversion_spec_argument,FlexRay_channel]
    p_preProcessConversion = subprocess.Popen(cmdList, stdout=None, stderr=None)
    if p_preProcessConversion is None:
        logger.error("Error: Failed to start preProcessConversion.py")

    time.sleep(1)

    #
    # Start CAPL-conversion script
    #
    print("create filetoconvert and start Capl_converter")

    postProcessFolder = "{}\{}".format(resultFolder, POST_PROCESS_IMPORT_FOLDER)
    print(postProcessFolder )
    # FO=FileOP ()
    # FO.del_file(postProcessFolder )
    runningName = "{}\{}".format(postProcessFolder, RUNNING_NAME)
    runningFP = open(runningName, "w")
    if runningFP is None:
        logger.error("Error: Failed to create file! Program aborted!")
        exit(FAIL)

    runningFP.close()

    logger.info("Start runCAPLconverter.py")
    cmdList = [PYTHON, "./runCAPLconverter.py", batchJobId, resultFolder, conversion_spec_argument]
    p_runCAPLconverter = subprocess.Popen(cmdList, stdout=None, stderr=None)
    if p_runCAPLconverter is None:
        logger.error("Error: Failed to start runCAPLconverter.py")

    time.sleep(1)

    #
    # Start post-conversion script
    #
    print("start Post conversion")
    logger.info("Start postProcessConversion.py")
    cmdList = [PYTHON, "./postProcessConversion.py", batchJobId, resultFolder, conversion_spec_argument]
    p_postProcessConversion = subprocess.Popen(cmdList, stdout=None, stderr=None)
    if p_postProcessConversion is None:
        logger.error("Error: Failed to start postProcessConversion.py")
    time.sleep(1)

    conversionRunning = True
    preProcessRunning = True
    CAPLconverterRunning = True
    CAPLconverterRunAttempt = 1
    postProcessRunning = True

    while conversionRunning:
        if p_preProcessConversion is not None and preProcessRunning:
            p_preProcessConversion.poll()
            if p_preProcessConversion.returncode is not None:
                #
                # Pre-processing is no longer ongoing
                #
                preProcessRunning = False
                os.remove("{}\{}".format(canoeFolder, RUNNING_NAME))

                if p_preProcessConversion.returncode != 0:
                    logger.error(
                        "Error: preProcessConversion.py exited with code {}".format(p_preProcessConversion.returncode))
                else:
                    logger.info("preProcessConversion.py exited successfully!")

        if p_runCAPLconverter is not None and CAPLconverterRunning:
            p_runCAPLconverter.poll()
            if p_runCAPLconverter.returncode is not None:
                #
                # CANoe converter is no longer ongoing
                #
                CAPLconverterRunning = False

                if p_runCAPLconverter.returncode != 0:
                    logger.error("Error: runCAPLconverter.py exited with code {}".format(p_runCAPLconverter.returncode))

                    if CAPLconverterRunAttempt < 6:
                        time.sleep(10)
                        CAPLconverterRunAttempt = CAPLconverterRunAttempt + 1

                        logger.info("Start runCAPLconverter.py attempt {}".format(CAPLconverterRunAttempt))
                        cmdList = [PYTHON, "./runCAPLconverter.py", batchJobId, resultFolder]
                        p_runCAPLconverter = subprocess.Popen(cmdList, stdout=None, stderr=None)
                        if p_runCAPLconverter is None:
                            logger.error("Error: Failed to start runCAPLconverter.py")
                            os.remove("{}\{}".format(postProcessFolder, RUNNING_NAME))
                        else:
                            CAPLconverterRunning = True
                    else:
                        os.remove("{}\{}".format(postProcessFolder, RUNNING_NAME))
                else:
                    logger.info("runCAPLconverter.py exited successfully!")
                    os.remove("{}\{}".format(postProcessFolder, RUNNING_NAME))

        if p_postProcessConversion is not None and postProcessRunning:
            p_postProcessConversion.poll()
            if p_postProcessConversion.returncode is not None:
                #
                # Post-process is no longer ongoing
                #
                postProcessRunning = False
                if p_postProcessConversion.returncode != 0:
                    logger.error("Error: postProcessConversion.py exited with code {}".format(
                        p_postProcessConversion.returncode))
                else:
                    logger.info("postProcessConversion.py exited successfully!")

        conversionRunning = preProcessRunning or CAPLconverterRunning or postProcessRunning
        time.sleep(1)

    logger.info("Conversion ended!")
    # with open(r"E:\GEEA2\time.txt", "a") as file:
    #     file.write(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    exit(SUCCESS)

