import logging
import os
import re
import socket
import subprocess
from argparse import ArgumentParser
from common.FileOperation import  *
import extractParamsFromDat
from common.constants import ADTF_EXPORTER, CANOE_IMPORT_FOLDER, LOG_FOLDER, TEMP_FOLDER, CANOE_JOB_FILE_NAME, \
    FAILED_PRE_PROCESS_JOBS,TMP_CURRENT_LINE_FILE_NAME
from common.datparser import get_flexray_streams
from common.logger import init_logging

#TMP_CURRENT_LINE_FILE_NAME = "tmpCurrentLinePreProcessing.txt"
SUM_FAILED_PRE_PROCESS_FILE_NAME = "SummaryOfFailedPreProcessingJobs.txt"

logger = logging.getLogger(__name__)

VERSION = "0.91"

job_counter = 0


class CreateFileError(Exception):
    pass


class CreateJobError(Exception):
    pass


def addFailedPreProcessJobs(fileName, inOutputFolder):
    failedPreProcessJobsFolder = "{}\{}".format(inOutputFolder, FAILED_PRE_PROCESS_JOBS)
    failedPreProcessJobsSummaryFile = "{}\{}".format(failedPreProcessJobsFolder, SUM_FAILED_PRE_PROCESS_FILE_NAME)

    with open(failedPreProcessJobsSummaryFile, "a") as fp:
        if fp is None:
            raise CreateFileError("Couldn't create file to store a failed pre-processing job.")
        else:
            fp.write(fileName + "\n")


def processFileList(inBatchJobId, inFileList, inOutputFolder, extract_parameters: bool):
    global job_counter

    if not os.path.isfile(inFileList):
        raise FileNotFoundError("Error: Input file list {} does not exist. Program aborted!".format(inFileList))

    tmpFolder = "{}\{}".format(inOutputFolder, TEMP_FOLDER)
    tmpCurrentLineFile = "{}\{}".format(tmpFolder, TMP_CURRENT_LINE_FILE_NAME)

    print(tmpCurrentLineFile )

    lastLineNumber = 0
    if os.path.isfile(tmpCurrentLineFile):
        #
        # Pre-process has been restarted, find where to proceed the pre-process work
        #
        pattern = re.compile("([0-9]+) ([0-9]+)")

        with open(tmpCurrentLineFile, "r") as fp:
            for line in fp:
                result = pattern.search(line)
                if result is not None:
                    lastLineNumber = int(result.group(1))
                    job_counter = int(result.group(2))

    plusSign = re.compile("^\+")
    hashTag = re.compile("[ ]*#.+$")
    # listOfFilesForConversion = []
    nextLineToRead = 1

    with open(inFileList) as fp:
        for line in fp:
            # listOfFilesForConversion.append(line)

            # for line in listOfFilesForConversion:
            #
            # Check if this is the line to start with
            #
            if (nextLineToRead != (lastLineNumber + 1)):
                nextLineToRead = nextLineToRead + 1
                continue

            result = hashTag.sub("", line)  # Remove comments
            if result is not None:
                line = result

            result = plusSign.sub("", line)  # Remove plus sign at first position if any

            if result is not None:
                fileName = result
            else:
                fileName = line

            removeLineFeed = re.compile("(.+)$")
            result = removeLineFeed.search(fileName)
            if result is not None:
                fileName = result.group(1)
                # print(len(fileName))
                # print(fileName)
                # logger.info(fileName)
                createSubJobForCANoe(inBatchJobId, fileName, inOutputFolder, extract_parameters)

            nextLineToRead = nextLineToRead + 1
            lastLineNumber = lastLineNumber + 1

            #
            # Store last processed line number in file list
            #
            with open(tmpCurrentLineFile, "a") as fd:
                if fd is None:
                    raise CreateFileError("Couldn't create {} to store last processed line "
                                          "in input file list".format(tmpCurrentLineFile))
                else:
                    lastLineNumberStr = str(lastLineNumber)
                    job_counterStr = str(job_counter)
                    fd.write(lastLineNumberStr + " " + job_counterStr + "\n")


def createSubJobForCANoe(inBatchJobId, inFileName, inOutputFolder, extract_parameters: bool):
    global job_counter

    if not os.path.isfile(inFileName):
        logger.warning("Input file {} does not exist. Proceed with next file.".format(inFileName))
        addFailedPreProcessJobs(inFileName, inOutputFolder)
        return

    if extract_parameters:
        extractParamsFromDat.extract(inFileName, os.path.join('.', 'parameterValues.cin'))

    nameWithoutPath = re.compile("([a-zA-Z0-9_\-]+)\.dat$")

    result = nameWithoutPath.search(inFileName)

    path = os.path.dirname(inFileName)
    filename, _ = os.path.splitext(inFileName)

#frank:this part does not need to do judgement ,because there only one stream in geea2.0
    # stream = ""
    # if args.DAI:
    #     json_path = os.path.join(path, '{}.json'.format(filename))
    #     flexray_streams = get_flexray_streams(json_path)
    # elif args.FLC2:
    #     json_path = os.path.join(path, '{}.json'.format(filename))
    #     flexray_streams = get_flexray_streams(json_path)   #frank:modified,because some json has no info about flexray sdb
    #
    #     # TODO This is hardcoded until we need to handle multiple extracts
    #     wanted_spec = ['213_238_257_CHASSIS_FlexRay_2016_42a',
    #                    '213_238_257_CHASSIS_FlexRay_2016_42a.arxml']
    #
    #     for stream_index, specification in flexray_streams.items():
    #         if specification in wanted_spec:
    #             stream = stream_index
    #             break
    #     else:
    #         raise ValueError('Could not find a matching flexray stream!')
    #
    #     if stream == 1:
    #         stream = ''
    #     else:
    #         stream = str(stream)

    if result is not None:
        ascName = result.group(1)
        if args.GEEA_CORE2E3U:
            ascName = "{}_CAN1.asc".format(ascName)  # for canfd edit by frank.zhang
        else:
            if FlexRay_channel=="FlexRay2":
                ascName = "{}_FlexRay2.asc".format(ascName)   # for flexray
            elif FlexRay_channel=="FlexRay":
                ascName = "{}_FlexRay.asc".format(ascName)
            else:
                ascName = "{}_FlexRay2.asc".format(ascName)# for flexray
        # ascName = "{}_CAN1.asc".format(ascName)    #for canfd edit by frank.zhang
        # ascName = "{}_FlexRay{}.asc".format(ascName, stream) # frank: do not  need to add stram number
        logger.info("Using flexray stream {}".format(ascName))
    else:
        logger.error("Error: Couldn't parse file name: {}".format(inFileName))
        logger.info("Proceed with next file.")
        addFailedPreProcessJobs(inFileName, inOutputFolder)
        return

    tmpFolder = "{}\{}".format(inOutputFolder, TEMP_FOLDER)
    logFolder = "{}\{}".format(inOutputFolder, LOG_FOLDER)

    targetFile = "{}\{}".format(tmpFolder, ascName)

    if not os.path.isfile(targetFile):
        logger.info("Extracting bus information for file {}".format(inFileName))
        ret = subprocess.call([ADTF_EXPORTER, "--log-path", logFolder, "--output-path", tmpFolder, inFileName])

        if (ret != 0):
            logger.error("Error: Failed to extract bus information! Proceed with next file.")
            addFailedPreProcessJobs(inFileName, inOutputFolder)
            return

    canoeFolder = "{}\{}".format(inOutputFolder, CANOE_IMPORT_FOLDER)
    jobName = "{}\{}_{}_{}.txt".format(canoeFolder, CANOE_JOB_FILE_NAME, inBatchJobId, str(job_counter).rjust(7, "0"))
    jobFP = open(jobName, "w")
    if (jobFP is None):
        raise CreateJobError("Error: Failed to create CANoe job! Proceed with next file.")

    jobFP.write("<Original file to convert>" + inFileName + "\n")
    jobFP.write("<Exported bus stream>" + ascName + "\n")

    jobFP.close()

    job_counter += 1


if __name__ == '__main__':
    parser = ArgumentParser(description='Preprocess CAPL conversion')
    parser.add_argument('-V', '--version', action='version', version='%%(prog)s (version %s)' % VERSION)
    parser.add_argument('-l', '--log-path', default=None, type=str, help='Path to store log files')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--flc2-resim-2910', dest='FLC2', action='store_true', help='FLC2 Resim with 2910 conversion')
    group.add_argument('--dai-to-flc2', dest='DAI', action='store_true', help='DAI to FLC2 conversion')
    # group.add_argument('--SVS-to-MVS', dest='Geea', action='store_true', help='svs to mvs conversion')
    group.add_argument('--E3U-to-MVS',dest= 'GEEA_E3U',action='store_true',help='E3U SVS2MVS conversion')
    group.add_argument('--E4-to-MVS',dest= 'GEEA_E4',action='store_true',help='E4 SVS2MVS conversion')
    group.add_argument('--core2E4-to-SVS', dest='GEEA_CORE2E3U', action='store_true', help='CORE 2 E4 SVS conversion')
    group.add_argument('--E3U2E4-to-SVS', dest='GEEA_E3U2E4', action='store_true', help='E3U 2 E4 SVS conversion')
    group.add_argument('--DAI2E4-to-SVS', dest='GEEA_DAI2E4', action='store_true', help='DAI 2 E4 SVS conversion')
    parser.add_argument('batchJobId', type=str, help='Job ID')
    parser.add_argument('fileList', type=str, help='Filelist to convert')
    parser.add_argument('resultFolder', type=str, help='Result folder')
    parser.add_argument('FlexRay_channel', type=str, help='Original Flexray channel')
    args = parser.parse_args()

    extract_parameters = False
    if args.DAI:
        extract_parameters = True
    elif args.GEEA_E3U:
        extract_parameters = False
    elif args.GEEA_E4:
        extract_parameters = False
    elif args.FLC2:
        # extract_parameters = True
        extract_parameters=True # for CANFD trail
    elif args.GEEA_CORE2E3U:
        extract_parameters = False
    elif args.GEEA_E3U2E4:
        extract_parameters = True
    elif args.GEEA_DAI2E4:
        extract_parameters =True

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

    # Perform pre-processing
    try:
        processFileList(batchJobId, fileList, resultFolder, extract_parameters)
    except Exception as e:
        logger.error(e)
        exit(1)
    exit(0)
