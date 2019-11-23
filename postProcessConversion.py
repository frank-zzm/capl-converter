import logging
import os
import re
import socket
import subprocess
import time
from argparse import ArgumentParser
from shutil import copyfile
from common.FileOperation import  *

from common.constants import LOG_FOLDER, RUNNING_NAME, POST_PROCESS_IMPORT_FOLDER, \
    FAILED_POST_PROCESS_JOBS, TEMP_FOLDER, RESULT_LIST_FILE, COM_MATRIX_ID, PRE_TAG_TEMP_ASC_FILE, ASC2ADTF,TMP_CURRENT_LINE_FILE_NAME
from common.logger import init_logging

logger = logging.getLogger(__name__)

VERSION = "0.95"


class RemoveJobError(Exception):
    pass


class TimestampError(Exception):
    pass


class CreateFileError(Exception):
    pass


class ParserState:
    SearchTriggerBlock = 0
    FindStartingTime = 1
    AdjustTime = 2
    FindEndTime = 3
    FinalizeLogFile = 4
    Error = 5
    FindStrngeFrame=0.5

    def __init__(self, _type):
        self.value = _type

    def __str__(self):
        if self.value == ParserState.SearchTriggerBlock:
            return 'SearchTriggerBlock'
        if self.value == ParserState.FindStartingTime:
            return 'FindStartingTime'
        if self.value==ParserState.FindStrngeFrame:
            return 'FindStrngeFrame'
        if self.value == ParserState.AdjustTime:
            return 'AdjustTime'
        if self.value == ParserState.FindEndTime:
            return 'FindEndTime'
        if self.value == ParserState.FinalizeLogFile:
            return 'FinalizeLogFile'
        if self.value == ParserState.Error:
            return 'Error'

    def __eq__(self, y):
        return self.value == y.value


def selectNextJob(inOutputFolder):
    postProcessFolder = "{}\{}\\".format(inOutputFolder, POST_PROCESS_IMPORT_FOLDER)
    jobList = [f for f in os.listdir(postProcessFolder) if
               (os.path.isfile(postProcessFolder + f) and f.endswith(".txt"))]

    runningFile = "{}\{}".format(postProcessFolder, RUNNING_NAME)
    logger.info("runningFile = {}".format(runningFile))
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

    logger.info("preProcessRunning = {}".format(preProcessRunning))
    return [preProcessRunning, jobsInQueue, nextJob]


def getFileToConvertFromJob(inOutputFolder, inJob):
    postProcessFolder = "{}\{}\\".format(inOutputFolder, POST_PROCESS_IMPORT_FOLDER)
    file = "{}\{}".format(postProcessFolder, inJob)
    with open(file) as fp:
        for line in fp:
            result = re.search("^<Exported bus stream>(.+)", line)
            if result is not None:
                fileToConvert = result.group(1)
            else:
                fileToConvert = ""

    fp.close()
    return fileToConvert


def removeJobFromQueue(inOutputFolder, inJob):
    postProcessFolder = "{}\{}\\".format(inOutputFolder, POST_PROCESS_IMPORT_FOLDER)
    srcFile = "{}\{}".format(postProcessFolder, inJob)

    failedPostProcessJobsFolder = "{}\{}".format(inOutputFolder, FAILED_POST_PROCESS_JOBS)
    dstFile = "{}\{}".format(failedPostProcessJobsFolder, inJob)

    try:
        copyfile(srcFile, dstFile)
    except Exception:
        logger.error("Error: Failed to copy job {}".format(inJob))

    try:
        os.remove(srcFile)
    except Exception:
        # If remove fails program execution will be stopped since otherwise program will enter infinite loop
        raise RemoveJobError("Error: Failed to remove job! Program aborted!")


def moveJobToFinnished(inOutputFolder, inJob, inDatFile):
    postProcessFolder = "{}\{}\\".format(inOutputFolder, POST_PROCESS_IMPORT_FOLDER)
    srcFile = "{}\{}".format(postProcessFolder, inJob)

    tmpFolder = "{}\{}".format(inOutputFolder, TEMP_FOLDER)
    dstFile = "{}\{}".format(tmpFolder, inJob)

    resultFile = "{}\{}".format(inOutputFolder, RESULT_LIST_FILE)

    with open(srcFile) as fp:
        for line in fp:
            logger.debug(line)
            result = re.search("^<Original file to convert>([\.\$:a-zA-Z0-9_\-\\\\]+)", line)
            if result is not None:
                fileThatWasConverted = result.group(1)
                logger.debug(fileThatWasConverted)
                break
            else:
                fileThatWasConverted = ""
                logger.debug("Problem")

    fp.close()

    if fileThatWasConverted != "":

        # result = re.search("([\.\$:a-zA-Z0-9_\-\\\\]*)([a-zA-Z0-9_\-]+)\.dat$", fileThatWasConverted)
        # result = re.sub("", "([a-zA-Z0-9_\-]+)\.[dD][aA][tT]$", fileThatWasConverted)
        result = re.search("([a-zA-Z0-9_\-]+)\.dat$", fileThatWasConverted)
        if result is not None:
            originalFileName = result.group(1)

        removeFileName = re.compile("[a-zA-Z0-9_\-]+\.dat$")
        result = removeFileName.sub("", fileThatWasConverted)

        if result is not None:
            originalPath = result
            logger.debug(originalPath)
            srcConvertedFile = "{}\{}".format(tmpFolder, inDatFile)
            dstConvertedFile = "{}{}_{}{}".format(originalPath, originalFileName, COM_MATRIX_ID, ".dat")

            try:
                copyfile(srcConvertedFile, dstConvertedFile)
            except Exception:
                logger.error("Error: Failed to copy {} to orignal folder".format(inDatFile))
                removeJobFromQueue(inOutputFolder, inJob)
                return
            else:
                with open(resultFile, "a") as fp:
                    if fp is not None:
                        fp.write(fileThatWasConverted + "\n")
                    else:
                        logger.info("Result file: {}".format(resultFile))
                        logger.info("Couldn't write {} to result file.".format(fileThatWasConverted))

    else:
        logger.error("Error: Failed to read which file that was converted!")

    try:
        copyfile(srcFile, dstFile)
    except Exception:
        logger.error("Error: Failed to move job {} to temp folder".format(inJob))

    try:
        os.remove(srcFile)
    except Exception:
        # If remove fails program execution will be stopped since otherwise program will enter infinite loop
        raise RemoveJobError("Error: Failed to remove job! Program aborted!")


def checkForFirstCycleForFrame(inSlotList, inLine):
    frame = re.compile("^[ ]+([0-9]+\.[0-9]{6}) "
                       "Fr RMSG([ ]+[0-9a-zA-Z]+){4}[ ]+([0-9a-zA-Z]+)[ ]+([0-9a-zA-Z]+) "
                       "Rx([ ]+[0-9a-zA-Z]+){5} ([0-9a-zA-Z]+)")

    lineIsFrame = frame.search(inLine)

    if lineIsFrame is None:
        return

    slotIdStr = "0x" + lineIsFrame.group(3)
    cycleNoStr = "0x" + lineIsFrame.group(4)

    # logger.debug("SlotId = {}".format(slotIdStr))
    # logger.debug("Cycle = {}".format(cycleNoStr))

    slotId = int(slotIdStr, 16)
    cycleNo = int(cycleNoStr, 16)

    row = 0
    arr = inSlotList[:, 1]

    for storedCycleNo in arr:
        if storedCycleNo == -1:
            inSlotList[row, 1] = cycleNo

        row = row + 1


def convertSecToMicroSec(timeStr):
    pos = timeStr.index(".", 0)
    if pos is ValueError:
        raise TimestampError("Error in timestamp from CANoe!")

    tmpStr = timeStr[pos + 1:]
    decimalPartStr = tmpStr.rjust(6, "0")
    secondsPartStr = timeStr[0:pos]

    microSec = int(decimalPartStr)
    microSec = microSec + int(secondsPartStr) * 1000000

    return microSec


def convertMicroSecToSec(time_to_convert):
    tmpStr = str(time_to_convert)
    tmpStrLength = len(tmpStr)

    if tmpStrLength > 6:
        seconds = tmpStr[0:tmpStrLength - 6] + "." + tmpStr[tmpStrLength - 6:]
    else:
        seconds = "0." + tmpStr.rjust(6, "0")

    return seconds


def returnTimeEntry(startPos, lineTable, cycleToMatch):
    row = startPos
    tableLength = len(lineTable)
    timeEntry = -1
    previousCycleNo = -1
    pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) "
                         "Fr RMSG([ ]+[0-9a-zA-Z]+){4}[ ]+([0-9a-zA-Z]+)[ ]+([0-9a-zA-Z]+) "
                         "[R|T]x([ ]+[0-9a-zA-Z]+){5} ([0-9a-zA-Z]+)")

    while timeEntry == -1 and row < tableLength:
        line = lineTable[row]
        result = pattern.search(line)

        if result is not None:
            cycleNoStr = "0x" + result.group(4)
            cycleNo = int(cycleNoStr, 16)

            if cycleNo == cycleToMatch:
                seconds = result.group(1)
                timeEntry = convertSecToMicroSec(seconds)

            if previousCycleNo == -1:
                previousCycleNo = cycleNo
            elif cycleNo != previousCycleNo:
                break

        if timeEntry == -1:
            row = row + 1

    return [row, timeEntry]


def processFile(originalAscFile, inOutputFolder, comMatrixIdentity, valid_first_frame_pattern):
    fileName = ""
    t = 0
    result = re.search("([a-zA-Z0-9_\-]+)\.asc$", originalAscFile)
    logger.debug("Input line: {}".format(originalAscFile))

    if result is not None:
        fileName = result.group(1)
    else:
        logger.debug("Couldn't interpret file name! File name = '{}'".format(originalAscFile))

    tmpFolder = "{}\{}".format(inOutputFolder, TEMP_FOLDER)

    convertedAscFile = "{}\{}{}.asc".format(tmpFolder, PRE_TAG_TEMP_ASC_FILE, fileName)

    originalAscFileWithPath = "{}\{}".format(tmpFolder, originalAscFile)
    logger.info("convertedAscFile is {}&orignalAscFiel is {}".format(convertedAscFile, originalAscFileWithPath))

    result = re.search("([a-zA-Z0-9_\-]+\.asc)$", originalAscFile)
    if result is None:
        raise FileNotFoundError("Couldn't interpret file name! File name = '{}'".format(originalAscFile))

    if not os.path.isfile(convertedAscFile):
        raise FileExistsError("Converted file path {} does not exist. Exiting...".format(convertedAscFile))

    tmpFolder = "{}\{}".format(inOutputFolder, TEMP_FOLDER)
    # outputFilename = outputFolder + "\" + convertedAscFile + "_" + comMatrixIdentity + ".asc"'
    outputFilename = "{}\{}_{}.asc".format(tmpFolder, fileName, comMatrixIdentity)
    logger.debug("Output file name: '{}'".format(outputFilename))
    outputFP = open(outputFilename, "w")
    if outputFP is None:
        raise CreateFileError("Couldn't create file {}!".format(outputFilename))

    state = ParserState(ParserState.SearchTriggerBlock)

    pattern = re.compile("^Begin Triggerblock ")

    # logger.debug("state = {}".format(state))
    originalData = []

    with open(originalAscFileWithPath) as fp:
        stopReadingFile = False

        for line in fp:
            if state == ParserState(ParserState.SearchTriggerBlock):
                # Do stuff
                result = pattern.search(line)

                if result is not None:
                    state = ParserState(ParserState.AdjustTime)
                    # pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) Fr RMSG")
                    pattern = re.compile(
                        "^[ ]+([0-9]+\.[0-9]{6}) "
                        "Fr RMSG([ ]+[0-9a-zA-Z]+){4}[ ]+([0-9a-zA-Z]+)[ ]+([0-9a-zA-Z]+) "
                        "[R|T]x([ ]+[0-9a-zA-Z]+){5} ([0-9a-zA-Z]+)")
                    # pattern = re.compile(VALID_Rx_ASDM2FLC_Frame )# Use for get first timestamp of Asdm->FLC data

            elif state == ParserState(ParserState.AdjustTime):
                # Do stuff
                result = pattern.search(line)

                if result is not None:
                    startTimeSourceFile = result.group(1)
                    startTime = convertSecToMicroSec(startTimeSourceFile)
                    endTime = startTime


                    # cycleNoStr = "0x" + result.group(4)
                    # cycleNo = int(cycleNoStr, 16)

                    # previousCycle = cycleNo

                    logger.debug("Starting time = {}".format(startTime))

                    # checkForFirstCycleForFrame(slotList, line)
                    originalData.append(line)

                    state = ParserState(ParserState.FindEndTime)

            elif state == ParserState(ParserState.FindEndTime):
                # Do stuff

                # result = re.search("(^[ ]+)([0-9]+\.[0-9]{6})( Fr RMSG.+$)", line)
                # targetStr = result.group(1) + adjustedTimeStr + result.group(3) + "\n"

                result = pattern.search(line)

                if result is not None:
                    timeSourceFile = result.group(1)
                    time_source_file_ms = convertSecToMicroSec(timeSourceFile)
                    if time_source_file_ms > endTime:
                        endTime = time_source_file_ms

                    # checkForFirstCycleForFrame(slotList, line)

                    # cycleNoStr = "0x" + result.group(4)
                    # cycleNo = int(cycleNoStr, 16)

                    # if ((cycleNo - previousCycle) < 0):
                    # cycles = 64 - previousCycle + cycleNo
                    # else:
                    # cycles = cycleNo - previousCycle

                    # if (cycles > 1):
                    # Missing cycles in original recording, add one dummy frame to fill out each missing cycle.
                    # This will necessary later when time adjustment is performed

                    originalData.append(line)

                else:
                    # logger.debug("End time = {}".format(endTime))
                    stopReadingFile = True

            if stopReadingFile:
                break

    fp.close()

    state = ParserState(ParserState.SearchTriggerBlock)
    pattern = re.compile("^Begin TriggerBlock ")

    validFirstFrame = re.compile(valid_first_frame_pattern)
    logger.info("validFirstFrame is {}".format(validFirstFrame ))
    foundValidFirstFrame = False

    # frame = re.compile("^[ ]+([0-9]+\.[0-9]{6}) Fr RMSG([ ]+[0-9a-zA-Z]+){6} Tx([ ]+[0-9a-zA-Z]+){5} ([a-zA-Z]+) ")
    frame = re.compile("^[ ]+([0-9]+\.[0-9]{6}) Fr RMSG([ ]+[0-9a-zA-Z]+){6} Tx([ ]+[0-9a-zA-Z]+){5} ([0-9a-zA-Z]+)")

    prevLogFileInfo = re.compile("^//[ ]+([0-9]+\.[0-9]{6}) previous log file:")

    validData = []

    intro = ["date Fri Aug 31 11:59:41.217 pm 2018\n",
             "base hex  timestamps absolute\n",
             "no internal events logged\n",
             "// version 10.0.1\n",
             "Begin TriggerBlock Fri Aug 31 11:59:41.662 pm 2018\n"]

    for row in intro:
        validData.append(row)

    with open(convertedAscFile) as fp:
        for line in fp:
            if state == ParserState(ParserState.SearchTriggerBlock):
                # Do stuff
                result = prevLogFileInfo.search(line)

                # if (result == None):
                #    # Only add line if it's not containing info about previous log file
                #    validData.append(line)

                result = pattern.search(line)
                # logger.debug(line)

                if result is not None:
                    state = ParserState(ParserState.FindStartingTime)
                    pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) TriggerEvent:")
            elif state==ParserState (ParserState .FindStrngeFrame ):
                res = pattern.search(line)

                if res is not None:
                    validData.append(line)

                state = ParserState(ParserState.FindStartingTime)
                pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) TriggerEvent:")

            elif state == ParserState(ParserState.FindStartingTime):
                res = pattern.search(line)

                if res is not None:
                    validData.append(line)

                # Trim non-valid data
                lineIsFrame = frame.search(line)

                if lineIsFrame is not None:
                    frameType = lineIsFrame.group(4)
                    # validData.append(line)# frank :add there, and then try to delete

               #deleted by frank
                if foundValidFirstFrame or lineIsFrame is not None:
                    validData.append(line)
                # logger.info("postProcessConvertion.py:res is {},lineIsFrame is {},foundValidFirstFrame is {} ,line value is{}".format(res,lineIsFrame,foundValidFirstFrame, line))
                #
                res = validFirstFrame.search(line)
                #
                if res is not None:
                    foundValidFirstFrame = True
    id7_triggerevent=validData [6]
    id6_validframe=validData [5]
    validData [5]=id7_triggerevent
    validData[6]=id6_validframe
    validData.append("End TriggerBlock\n")
    # with open(r"E:\GEEA2\Temp\validData.txt",'a') as file:
    #     for i in validData :
    #         file.write(i)


    fp.close()
    # 暂时关闭数据的log
    # logger.info("validData is {}".format(validData ))

    pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) "
                         "Fr RMSG([ ]+[0-9a-zA-Z]+){4}[ ]+([0-9a-zA-Z]+)[ ]+([0-9a-zA-Z]+) "
                         "[R|T]x([ ]+[0-9a-zA-Z]+){5} ([0-9a-zA-Z]+)")

    line = originalData[0]
    result = pattern.search(line)
    if result is not None:
        cycleNoStr = "0x" + result.group(4)
        originalStartCycleNo = int(cycleNoStr, 16)

    state = ParserState(ParserState.SearchTriggerBlock)
    pattern = re.compile("^Begin TriggerBlock ")

    for line in validData:

        if state == ParserState(ParserState.SearchTriggerBlock):
            # Do stuff
            result = pattern.search(line)
            # logger.debug(line)
            outputFP.write(line)

            if result is not None:
                state = ParserState(ParserState.FindStartingTime)
                pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) TriggerEvent:")

        elif state == ParserState(ParserState.FindStartingTime):
            # Do stuff
            result = pattern.search(line)
            logger.debug("starting str is {0}".format(result))

            if result is not None:
                outputFP.write("   0.000000 Start of measurement\n")
                startTimeEntry = result.group(1)
                # pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) Fr RMSG")
                pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) "
                                     "Fr RMSG([ ]+[0-9a-zA-Z]+){4}[ ]+([0-9a-zA-Z]+)[ ]+([0-9a-zA-Z]+) "
                                     "[R|T]x([ ]+[0-9a-zA-Z]+){5} ([0-9a-zA-Z]+)")
                previousCycle = -1
                timeOffset = 0
                currentRowInOriginalData = 0

                state = ParserState(ParserState.AdjustTime)

        elif state == ParserState(ParserState.AdjustTime):
            # Do stuff
            result = pattern.search(line)
            # logger.debug(line)

            if result is not None:
                timeEntry = result.group(1)
                cycleNoStr = "0x" + result.group(4)
                cycleNo = int(cycleNoStr, 16)
                # logger.debug("the timeEntry is {0}; the cycleNo is {1}".format(timeEntry ,cycleNo))
                # wait for analize
                if previousCycle == -1:
                    adjustedTime = startTime #add 5000 by frankzHANG
                    adjustedTimeStr = convertMicroSecToSec(adjustedTime)
                    previousCycle = cycleNo
                    cycleOffset = cycleNo - originalStartCycleNo
                    if cycleOffset < 0:
                        # Take care of wraparound
                        cycleOffset = cycleOffset + 0x40

                    dbgStr = "originalStartCycleNo={}".format(originalStartCycleNo)
                    dbgStr = dbgStr + "    cycleNo={}".format(cycleNo)
                    dbgStr = dbgStr + "    cycleOffset={}".format(cycleOffset)
                    # logger.debug(dbgStr)

                elif previousCycle == cycleNo:
                    # adjustedTime = startTime + timeOffset
                    adjustedTimeStr = convertMicroSecToSec(adjustedTime)
                else:
                    # Handle wraparound
                    if (cycleNo - previousCycle) < 0:
                        cycles = 64 - previousCycle + cycleNo
                    else:
                        cycles = cycleNo - previousCycle

                    # logger.debug("currentRowInOriginalData = {}".format(currentRowInOriginalData))
                    # logger.debug("originalData = {}".format(len(originalData)))
                    # logger.debug("cycleNo = {}".format(cycleNo))

                    cycleToMatch = cycleNo - cycleOffset
                    if cycleToMatch < 0:
                        # Take care of wraparound
                        cycleToMatch = cycleToMatch + 0x40

                    [timeEntryRow, originalTime] = returnTimeEntry(currentRowInOriginalData, originalData, cycleToMatch)
                    logger.debug("debug time is {2};timeEntryRow = {0};originalTime = {1}".format(timeEntryRow,originalTime,time.time()))

                    dbgStr = "timeEntryRow={}".format(timeEntryRow)
                    dbgStr = dbgStr + "    originalTime={}".format(originalTime)
                    dbgStr = dbgStr + "    currentRowInOriginalData={}".format(currentRowInOriginalData)
                    dbgStr = dbgStr + "    cycleToMatch={}".format(cycleToMatch)
                    # logger.debug(dbgStr)

                    if originalTime == -1:
                        adjustedTime = adjustedTime + 5000 * cycles# 5000 is added by frank.zhang
                        # logger.debug("adjustedTime={}   cycles={}".format(adjustedTime, cycles))
                    else:
                        adjustedTime = originalTime# 5000 is added by frank.zhang
                        currentRowInOriginalData = timeEntryRow

                    # if (cycles == 1):
                    #    [timeEntryRow, originalTime] = returnTimeStr(currentRowInOriginalData, originalData, cycleNo)
                    #    timeOffset = timeOffset + 5000*cycles
                    # else:
                    #    timeOffset = timeOffset + 5000

                    # adjustedTime = startTime + timeOffset
                    adjustedTimeStr = convertMicroSecToSec(adjustedTime)
                    previousCycle = cycleNo

                # logger.debug(adjustedTimeStr)

                result = re.search("(^[ ]+)([0-9]+\.[0-9]{6})( Fr RMSG.+$)", line)
                targetStr = result.group(1) + adjustedTimeStr + result.group(3) + "\n"

                if (t<=5):
                    logger.debug("the current line is {0}".format(line))
                    logger.debug("the time is {3};the targetStr = {0};group(1) ={1},group(3)={2}".format(targetStr,result.group(1),result .group(3) ,time.time() ))
                    t=t+1
                if adjustedTime <= endTime:
                    outputFP.write(targetStr)
                else:
                    state = ParserState(ParserState.FinalizeLogFile)

            else:
                result = re.search("End TriggerBlock", line)
                if result is not None:
                    outputFP.write(line)

        elif state == ParserState(ParserState.FinalizeLogFile):
            result = re.search("End TriggerBlock", line)
            if result is not None:
                outputFP.write(line)

    outputFP.close()

    logFolder = "{}\{}".format(inOutputFolder, LOG_FOLDER)
    inputFile = "{}\{}_{}.asc".format(tmpFolder, fileName, comMatrixIdentity)
    ret = subprocess.call([ASC2ADTF, "--log-path", logFolder, "--output-dir", tmpFolder, "--input-file", inputFile])

    datFileName = "{}_{}.dat".format(fileName, comMatrixIdentity)

    return [ret, datFileName]

def process2FrFile(originalAscFile, inOutputFolder, comMatrixIdentity, valid_first_frame_pattern):
    fileName = ""
    t = 0
    result = re.search("([a-zA-Z0-9_\-]+)\.asc$", originalAscFile)
    logger.debug("Input line: {}".format(originalAscFile))

    if result is not None:
        fileName = result.group(1)
    else:
        logger.debug("Couldn't interpret file name! File name = '{}'".format(originalAscFile))

    tmpFolder = "{}\{}".format(inOutputFolder, TEMP_FOLDER)

    convertedAscFile = "{}\{}{}.asc".format(tmpFolder, PRE_TAG_TEMP_ASC_FILE, fileName)

    originalAscFileWithPath = "{}\{}".format(tmpFolder, originalAscFile)
    logger.info("convertedAscFile is {}&orignalAscFiel is {}".format(convertedAscFile, originalAscFileWithPath))

    result = re.search("([a-zA-Z0-9_\-]+\.asc)$", originalAscFile)
    if result is None:
        raise FileNotFoundError("Couldn't interpret file name! File name = '{}'".format(originalAscFile))

    if not os.path.isfile(convertedAscFile):
        raise FileExistsError("Converted file path {} does not exist. Exiting...".format(convertedAscFile))

    tmpFolder = "{}\{}".format(inOutputFolder, TEMP_FOLDER)
    # outputFilename = outputFolder + "\" + convertedAscFile + "_" + comMatrixIdentity + ".asc"'
    outputFilename = "{}\{}_{}.asc".format(tmpFolder, fileName, comMatrixIdentity)
    logger.debug("Output file name: '{}'".format(outputFilename))
    outputFP = open(outputFilename, "w")
    if outputFP is None:
        raise CreateFileError("Couldn't create file {}!".format(outputFilename))


    validData = []

    intro = ["date Fri Aug 31 11:59:41.217 pm 2018\n",
             "base hex  timestamps absolute\n",
             "no internal events logged\n",
             "// version 10.0.1\n",
             "Begin TriggerBlock Fri Aug 31 11:59:41.662 pm 2018\n"
             "   0.000000 Start of measurement\n"]

    for row in intro:
        validData.append(row)

    ori_pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) " "Start of measurement")
    startTime = 0
    with open(originalAscFileWithPath, 'r')as fp:
        for line in fp:
            result = re.search(ori_pattern, line)
            if result is not None:
                startTime = float(result.group(1))

    frames_result = []
    pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) Fr RMSG([ ]+[0-9a-zA-Z]+){4}[ ]+([0-5]+)[ ]+([0-9a-zA-Z]+) ")
    with open(convertedAscFile, 'r') as fp:
        for line in fp:
            result = re.search(pattern, line)

            if result is not None:
                timestamp = startTime + float(result.group(1))

                # print(timestamp)
                # print(str(timestamp))
                thus_str = line.replace(result.group(1), "%.6f"%timestamp)
                # logger.info(
                #     "startTime: {0}: timestamp:{1},floatTime: {2}".format(startTime, thus_str, float(result.group(1))))
                # print("thus_str:", thus_str)
                frames_result.append(thus_str)
    validData.extend(frames_result)
    endtriger = ["End TriggerBlock\n"]
    validData.extend(endtriger)
    with open(outputFilename, 'w+') as fp:
        for i in validData:
            fp.write(i)


    logFolder = "{}\{}".format(inOutputFolder, LOG_FOLDER)
    inputFile = "{}\{}_{}.asc".format(tmpFolder, fileName, comMatrixIdentity)
    ret = subprocess.call([ASC2ADTF, "--log-path", logFolder, "--output-dir", tmpFolder, "--input-file", inputFile])

    datFileName = "{}_{}.dat".format(fileName, comMatrixIdentity)

    return [ret, datFileName]
if __name__ == '__main__':
    parser = ArgumentParser(description='Postprocess CAPL conversion')
    parser.add_argument('-V', '--version', action='version', version='%%(prog)s (version %s)' % VERSION)
    parser.add_argument('-l', '--log-path', default=None, type=str, help='Path to store log files')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--flc2-resim-2910', dest='FLC2', action='store_true', help='FLC2 Resim with 2910 conversion')
    group.add_argument('--dai-to-flc2', dest='DAI', action='store_true', help='DAI to FLC2 conversion')

    group.add_argument('--E3U-to-MVS',dest= 'GEEA_E3U',action='store_true',help='E3U SVS2MVS conversion')
    group.add_argument('--E4-to-MVS',dest= 'GEEA_E4',action='store_true',help='E4 SVS2MVS conversion')
    group.add_argument('--core2E4-to-SVS', dest='GEEA_CORE2E3U', action='store_true', help='CORE 2 E4 SVS conversion')
    group.add_argument('--E3U2E4-to-SVS', dest='GEEA_E3U2E4', action='store_true', help='E3U 2 E4 SVS conversion')
    group.add_argument('--DAI2E4-to-SVS', dest='GEEA_DAI2E4', action='store_true', help='DAI 2 E4 SVS conversion')
    parser.add_argument('batchJobId', type=str, help='Job ID')
    parser.add_argument('resultFolder', type=str, help='Result folder')
    args = parser.parse_args()

    if args.FLC2:
        from common.constants_flc2 import VALID_FIRST_FRAME_PATTERN,VALID_Rx_ASDM2FLC_Frame
    elif args.DAI:
        from common.constants_dai import VALID_FIRST_FRAME_PATTERN
    elif args.GEEA_E3U:
        from common.constants_Geely  import VALID_FIRST_FRAME_PATTERN
    elif args.GEEA_E4:
        from common.constants_Geely import VALID_FIRST_FRAME_PATTERN
    elif  args.GEEA_E3U2E4:
        from common.constants_Geely import VALID_FIRST_FRAME_PATTERN
    elif args.GEEA_CORE2E3U:
        from common.constants_Geely import VALID_FIRST_FRAME_PATTERN
    elif args.GEEA_DAI2E4:
        from common.constants_Geely import VALID_FIRST_FRAME_PATTERN

    else:
        raise NotImplementedError('No project configuration specified!')

    # Inputs
    batchJobId = args.batchJobId
    resultFolder = args.resultFolder

    # Initialize rotating log files
    logpath = args.log_path if args.log_path else "{}\{}".format(resultFolder, LOG_FOLDER)
    filename = "{host}.{name}.log".format(host=socket.gethostname(),
                                          name=os.path.splitext(os.path.basename(__file__))[0])
    filepath = os.path.abspath(os.path.join(logpath, filename))
    init_logging(log_file=filepath, max_file_size_mb=5, max_backup_count=10)

    logger.info("Version {}".format(VERSION))

    # Perform post-processing
    jobsWaitingToBeProcessed = True
    canoeConversionRunning = True

    try:
        while jobsWaitingToBeProcessed or canoeConversionRunning:
            # del jobList[:]

            # [canoeConversionRunning, jobsWaitingToBeProcessed, currentJob] = selectNextJob(resultFolder, jobList)
            [canoeConversionRunning, jobsWaitingToBeProcessed, currentJob] = selectNextJob(resultFolder)

            logger.info("Read job: {}".format(currentJob))

            if jobsWaitingToBeProcessed:
                fileToPostProcess = getFileToConvertFromJob(resultFolder, currentJob)
            else:
                # Wait for producer to create more jobs
                time.sleep(10)
                logger.info("cannoeConversionRunning?{}".format(canoeConversionRunning ))
                continue

            if fileToPostProcess == "":
                logger.error("Error: Failed to read file to post-process from job! Proceeding with next file.")
                removeJobFromQueue(resultFolder, currentJob)
                continue

            logger.info("File to post-process: {}".format(fileToPostProcess))
            if args.GEEA_CORE2E3U:
                [retFromAsc2Dat, datFile] = process2FrFile(fileToPostProcess, resultFolder, COM_MATRIX_ID,
                                                                VALID_FIRST_FRAME_PATTERN)
            elif args.GEEA_DAI2E4:
                [retFromAsc2Dat, datFile] = processFile(fileToPostProcess, resultFolder, COM_MATRIX_ID,
                                                                VALID_FIRST_FRAME_PATTERN)
            else:
                [retFromAsc2Dat, datFile] = processFile(fileToPostProcess, resultFolder, COM_MATRIX_ID,
                                                        VALID_FIRST_FRAME_PATTERN)


            if retFromAsc2Dat == 0:
                logger.info("Post-processing ended for job {}".format(currentJob))
                moveJobToFinnished(resultFolder, currentJob, datFile)
                logger.info("Job {} moved to list of finished jobs".format(currentJob))
            else:
                logger.error("Error: Failed to run Asc2Dat for job {} Proceed with next file!".format(currentJob))
                removeJobFromQueue(resultFolder, currentJob)
    except Exception as e:
        logger.error(e)
        exit(1)
    tmpFolder = "{}\\\{}".format(resultFolder, TEMP_FOLDER)
    print("the post part is {0}".format( tmpFolder ))
    tmpCurrentLineFile = "{}\\\{}".format(tmpFolder, TMP_CURRENT_LINE_FILE_NAME)
    print("the post tmpcurrentlinefile is {0}".format(tmpCurrentLineFile))
    FO=FileOP ()
    FO.del_file(tmpCurrentLineFile)

    exit(0)
