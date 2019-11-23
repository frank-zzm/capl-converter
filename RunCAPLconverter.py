import logging
import os
import re
import socket
import time
from argparse import ArgumentParser
from shutil import copyfile

from common.canoe import CanoeSync
from common.constants import CANOE_IMPORT_FOLDER, LOG_FOLDER, TEMP_FOLDER, PRE_TAG_TEMP_ASC_FILE, RUNNING_NAME, \
    POST_PROCESS_IMPORT_FOLDER, FAILED_CANOE_JOBS
from common.logger import init_logging

VERSION = "0.91"

logger = logging.getLogger(__name__)


class CAPLConversionError(Exception):
    pass


def createCAPLincludeFile(inOutputFolder, inFileToConvert):
    logger.info("Create CAPL include file for {}".format(inFileToConvert))

    canoeIncludeFP = open("fileToConvert.cin", "w")
    if canoeIncludeFP is None:
        logger.error("ERROR: Failed to create include file for CANoe! Proceed with next file.")
        return False

    fileWithPath = "{}\\\\{}\\\\{}".format(inOutputFolder, TEMP_FOLDER, inFileToConvert)
    loggingFileWithPath = "{}\\\\{}\\\\{}{}".format(inOutputFolder, TEMP_FOLDER, PRE_TAG_TEMP_ASC_FILE, inFileToConvert)

    canoeIncludeFP.write("/*@!Encoding:1252*/" + "\n")
    canoeIncludeFP.write("variables" + "\n")
    canoeIncludeFP.write("{" + "\n")
    canoeIncludeFP.write("  char fileToConvert[500] = \"{}\";".format(fileWithPath) + "\n")
    canoeIncludeFP.write("  char loggingFile[500] = \"{}\";".format(loggingFileWithPath) + "\n")
    canoeIncludeFP.write("}" + "\n")
    canoeIncludeFP.write("\n")

    canoeIncludeFP.close()

    return True


def selectNextJob(inOutputFolder):
    canoeFolder = "{}\{}\\".format(inOutputFolder, CANOE_IMPORT_FOLDER)
    jobList = [f for f in os.listdir(canoeFolder) if (os.path.isfile(canoeFolder + f) and f.endswith(".txt"))]

    runningFile = "{}\{}".format(canoeFolder, RUNNING_NAME)
    logger.info("canoeFolder = ".format(canoeFolder))
    logger.info("runningFile = ".format(runningFile))
    if os.path.isfile(runningFile):
        preProcessRunning = True
    else:
        preProcessRunning = False

    jobList.sort()

    if len(jobList) != 0:
        nextJob = jobList[0]
        jobsInQueue = True
    else:
        nextJob = ""
        jobsInQueue = False

    return [preProcessRunning, jobsInQueue, nextJob]


def getFileToConvertFromJob(inOutputFolder, inJob):
    canoeFolder = "{}\{}\\".format(inOutputFolder, CANOE_IMPORT_FOLDER)
    file = "{}\{}".format(canoeFolder, inJob)
    with open(file) as fp:
        for line in fp:
            result = re.search("^<Exported bus stream>(.+)", line)
            if result is not None:
                fileToConvert = result.group(1)
            else:
                fileToConvert = ""
    return fileToConvert


def removeJobFromQueue(inOutputFolder, inJob):
    canoeFolder = "{}\{}\\".format(inOutputFolder, CANOE_IMPORT_FOLDER)
    srcFile = "{}\{}".format(canoeFolder, inJob)

    failedCANoeJobsFolder = "{}\{}".format(inOutputFolder, FAILED_CANOE_JOBS)
    dstFile = "{}\{}".format(failedCANoeJobsFolder, inJob)

    try:
        copyfile(srcFile, dstFile)
    except Exception:
        logger.error("ERROR: Failed to copy job {}".format(inJob))

    try:
        os.remove(srcFile)
    except Exception:
        # If remove fails program execution will be stopped since otherwise program will enter infinite loop
        raise CAPLConversionError("ERROR: Failed to remove job! Program aborted!")


def moveJobToPostProcessQueue(inOutputFolder, inJob):
    canoeFolder = "{}\{}\\".format(inOutputFolder, CANOE_IMPORT_FOLDER)
    srcFile = "{}\{}".format(canoeFolder, inJob)

    postProcessFolder = "{}\{}".format(inOutputFolder, POST_PROCESS_IMPORT_FOLDER)
    dstFile = "{}\{}".format(postProcessFolder, inJob)

    try:
        copyfile(srcFile, dstFile)
    except Exception:
        logger.error("ERROR: Failed to move job {} to post-process queue".format(inJob))

    try:
        os.remove(srcFile)
    except Exception:
        # If remove fails program execution will be stopped since otherwise program will enter infinite loop
        raise CAPLConversionError("ERROR: Failed to remove job! Program aborted!")


if __name__ == '__main__':
    parser = ArgumentParser(description='CAPL converter')
    parser.add_argument('-V', '--version', action='version', version='%%(prog)s (version %s)' % VERSION)
    parser.add_argument('-l', '--log-path', default=None, type=str, help='Path to store log files')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--flc2-resim-2910', dest='FLC2', action='store_true', help='FLC2 Resim with 2910 conversion')
    group.add_argument('--dai-to-flc2', dest='DAI', action='store_true', help='DAI to FLC2 conversion')

    group.add_argument('--E3U-to-MVS',dest= 'GEEA_E3U',action='store_true',help='E3U SVS2MVS conversion')
    group.add_argument('--E4-to-MVS',dest= 'GEEA_E4',action='store_true',help='E4 SVS2MVS conversion')
    group.add_argument('--core2E4-to-SVS', dest='GEEA_CORE2E3U', action='store_true', help='CORE 2 E4 SVS conversion')
    group.add_argument('--DAI2E4-to-SVS', dest='GEEA_DAI2E4', action='store_true', help='DAI 2 E4 SVS conversion')
    group.add_argument('--E3U2E4-to-SVS', dest='GEEA_E3U2E4', action='store_true', help='E3U 2 E4 SVS conversion')

    parser.add_argument('batchJobId', type=str, help='Job ID')
    parser.add_argument('resultFolder', type=str, help='Result folder')
    args = parser.parse_args()

    # Inputs
    batchJobId = args.batchJobId
    resultFolder = args.resultFolder

    # Set up logging
    logpath = "{}\{}".format(resultFolder, LOG_FOLDER)
    filename = "{host}.{name}.log".format(host=socket.gethostname(),
                                          name=os.path.splitext(os.path.basename(__file__))[0])
    filepath = os.path.abspath(os.path.join(logpath, filename))
    init_logging(log_file=filepath, max_file_size_mb=5, max_backup_count=10)

    logger.info("Version {}".format(VERSION))

    if args.FLC2:
        from common.constants_flc2 import CAPL_CONFIG_FILE
    elif args.DAI:
        from common.constants_dai import CAPL_CONFIG_FILE
    elif args.GEEA_E3U:
        from common.constants_Geely import  CAPL_CONFIG_FILE_E3U as CAPL_CONFIG_FILE
    elif args.GEEA_E4:
        from common.constants_Geely import CAPL_CONFIG_FILE_E4 as CAPL_CONFIG_FILE
    elif  args.GEEA_E3U2E4:
        from common.constants_Geely import CAPL_CONFIG_FILE_E3U2E4 as CAPL_CONFIG_FILE
    elif args.GEEA_CORE2E3U:
        from common.constants_Geely import CAPL_CONFIG_FILE_Core2E3U as CAPL_CONFIG_FILE
    elif args.GEEA_DAI2E4:
        from common.constants_Geely import  CAPL_CONFIG_FILE_DAI2E4  as CAPL_CONFIG_FILE
    else:
        raise NotImplementedError('No project configuration specified!')

    # Loads CANoe configuration
    app = CanoeSync()
    try:
        app.Load(CAPL_CONFIG_FILE)

        jobsWaitingToBeProcessed = True
        preProcessConversionRunning = True

        while jobsWaitingToBeProcessed or preProcessConversionRunning:
            # del jobList[:]
            compilationFailed = False

            # [preProcessConversionRunning, jobsWaitingToBeProcessed, currentJob] = selectNextJob(resultFolder, jobList)
            [preProcessConversionRunning, jobsWaitingToBeProcessed, currentJob] = selectNextJob(resultFolder)

            logger.info("Read job: {}".format(currentJob))

            if jobsWaitingToBeProcessed:
                fileToConvert = getFileToConvertFromJob(resultFolder, currentJob)
            else:
                # Wait for producer to create more jobs
                app.SleepWithMessagePump(1000)
                continue

            if fileToConvert == "":
                logger.error("ERROR: Failed to read file to convert from job! Proceeding with next file.")
                removeJobFromQueue(resultFolder, currentJob)
                continue

            logger.info("File to convert: {}".format(fileToConvert))

            maxNumberOfAttempts = 5
            for i in range(0, maxNumberOfAttempts):
                ret = createCAPLincludeFile(resultFolder, fileToConvert)
                if ret == False:
                    # Something went wrong, remove job from queue
                    removeJobFromQueue(resultFolder, currentJob)
                    compilationFailed = True
                    # continue
                    break

                # # start the measurement
                # app.StartWithTimeout()
                app.StartForMsgPump()

                if app.MessagePump() == False:
                    logger.debug("Quit message from Windows")

                # Check if start of conversion failed
                if app.LatestCompileResult() == 1:
                    logger.error("ERROR: Compilation failed! Make another attempt.")
                    # removeJobFromQueue(resultFolder, currentJob)
                    # time.sleep(1)
                    app.SleepWithMessagePump(1000)
                    compilationFailed = True
                    continue
                else:
                    compilationFailed = False

                logger.info("Conversion started for job {}".format(currentJob))
                startTime = time.time()

                # #while not msvcrt.kbhit():
                while app.CheckRunning():
                    # DoEvents()
                    if app.MessagePump() == False:
                        logger.debug("Quit message from Windows")

                logger.info("Conversion ended for job {}".format(currentJob))

                endTime = time.time()
                if (endTime - startTime) < 5:
                    # Conversion was probably aborted directly
                    logger.info("Job {} aborted immediately. Attempt number {}".format(currentJob, i + 1))

                    for _ in range(1, 10):
                        # time.sleep(1)
                        # DoEvents()
                        app.SleepWithMessagePump(1000)

                    continue
                else:
                    break

            if (endTime - startTime) < 5 or compilationFailed:
                logger.error("ERROR: Job {} has failed {} times. "
                             "Remove it from queue and proceed.".format(currentJob, maxNumberOfAttempts))
                removeJobFromQueue(resultFolder, currentJob)
            else:
                logger.info("Job {} passed on to post-processing".format(currentJob))
                moveJobToPostProcessQueue(resultFolder, currentJob)
    except Exception as e:
        logger.error(e)
        logger.info("load canoe config file failed")
        exit(1)
    finally:
        # Exit CANoe
        app.Configuration.Modified = False
        app.Quit()
        logger.info("exit CANOE app")
    exit(0)
