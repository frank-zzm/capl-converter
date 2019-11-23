import os
import re
import sys

from common.constants import CANOE_IMPORT_FOLDER, LOG_FOLDER, FAILED_CANOE_JOBS, TEMP_FOLDER, \
    POST_PROCESS_IMPORT_FOLDER, FAILED_POST_PROCESS_JOBS, FAILED_PRE_PROCESS_JOBS

VERSION = "1.0"
PROGRAM_NAME = "prepareForConversionTools.py"

    
def main():
    batchJobId = sys.argv[1]
    fileList = sys.argv[2]
    resultFolder = sys.argv[3]
    FlexRay_channel=sys.argv[4]
    

    if not os.path.isfile(fileList):
        print("Error: Input file list {} does not exist. Program aborted!".format(fileList))
        sys.exit(2)
    
    if (os.path.isdir(resultFolder) == False):
        os.makedirs(resultFolder)

        logFolder = "{}\{}".format(resultFolder, LOG_FOLDER)
        os.makedirs(logFolder)
        
        tmpFolder = "{}\{}".format(resultFolder, TEMP_FOLDER)
        os.makedirs(tmpFolder)
        
        failedPreProcessJobsFolder = "{}\{}".format(resultFolder, FAILED_PRE_PROCESS_JOBS)
        os.makedirs(failedPreProcessJobsFolder)

        canoeFolder = "{}\{}".format(resultFolder, CANOE_IMPORT_FOLDER)
        os.makedirs(canoeFolder)

        failedCANoeJobsFolder = "{}\{}".format(resultFolder, FAILED_CANOE_JOBS)
        os.makedirs(failedCANoeJobsFolder)
        
        postProcessFolder = "{}\{}".format(resultFolder, POST_PROCESS_IMPORT_FOLDER)
        os.makedirs(postProcessFolder)

        failedPostProcessJobsFolder = "{}\{}".format(resultFolder, FAILED_POST_PROCESS_JOBS)
        os.makedirs(failedPostProcessJobsFolder)

    else:
        logFolder = "{}\{}".format(resultFolder, LOG_FOLDER)
        if (os.path.isdir(logFolder) == False):
            os.makedirs(logFolder)
            
        tmpFolder = "{}\{}".format(resultFolder, TEMP_FOLDER)
        if (os.path.isdir(tmpFolder) == False):
            os.makedirs(tmpFolder)

        failedPreProcessJobsFolder = "{}\{}".format(resultFolder, FAILED_PRE_PROCESS_JOBS)
        if (os.path.isdir(failedPreProcessJobsFolder) == False):
            os.makedirs(failedPreProcessJobsFolder)

        
        canoeFolder = "{}\{}".format(resultFolder, CANOE_IMPORT_FOLDER)
        if (os.path.isdir(canoeFolder) == False):
            os.makedirs(canoeFolder)

        failedCANoeJobsFolder = "{}\{}".format(resultFolder, FAILED_CANOE_JOBS)
        if (os.path.isdir(failedCANoeJobsFolder) == False):
            os.makedirs(failedCANoeJobsFolder)

        postProcessFolder = "{}\{}".format(resultFolder, POST_PROCESS_IMPORT_FOLDER)
        if (os.path.isdir(postProcessFolder) == False):
            os.makedirs(postProcessFolder)

        failedPostProcessJobsFolder = "{}\{}".format(resultFolder, FAILED_POST_PROCESS_JOBS)
        if (os.path.isdir(failedPostProcessJobsFolder) == False):
            os.makedirs(failedPostProcessJobsFolder)

    if (    (os.path.isdir(resultFolder) == False) or
            (os.path.isdir(logFolder) == False) or
            (os.path.isdir(tmpFolder) == False) or
            (os.path.isdir(canoeFolder) == False) or
            (os.path.isdir(failedCANoeJobsFolder) == False) or
            (os.path.isdir(postProcessFolder) == False) or
            (os.path.isdir(failedPostProcessJobsFolder) == False)):
        
        print("Error: Failed to create working folder! Program aborted!")
        sys.exit(1)
    
    
    checkBatchJobId = re.search("([a-zA-Z0-9_\-]+)", batchJobId)
    if (checkBatchJobId != None):
        tmpStr = checkBatchJobId.group(1)
        if (tmpStr != batchJobId):
            print("Error: Not a valid batch job id! Program aborted!")
            sys.exit(2)
    else:
        print("Error: Not a valid batch job id! Program aborted!")
        sys.exit(2)
    
    
    
if __name__ == '__main__':

   main()
   print('prepare , make log file directory')
