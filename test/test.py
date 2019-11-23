# # import os
# # path = r"E:\\GEEA2\\G2SVS4_Stereo_PIAE1025_20190610_100853_SPA2910.dat"
# # # with open(path,'r') as file:
# # #     print(file.read() )
# # def del_file(path):
# #     if os.path.isfile(path):
# #         os.remove(path)
# #     else:
# #       for i in os.listdir(path):
# #           path_file = os.path.join(path, i) #// 取文件绝对路径
# #           if os.path.isfile(path_file):
# #               os.remove(path_file)
# #           else:
# #               del_file(path_file)
# # del_file(path)
# import logging
# import os
# import re
# import socket
# import subprocess
# import time
# from argparse import ArgumentParser
# from shutil import copyfile
# from common.FileOperation import  *
#
# from common.constants import LOG_FOLDER, RUNNING_NAME, POST_PROCESS_IMPORT_FOLDER, \
#     FAILED_POST_PROCESS_JOBS, TEMP_FOLDER, RESULT_LIST_FILE, COM_MATRIX_ID, PRE_TAG_TEMP_ASC_FILE, ASC2ADTF,TMP_CURRENT_LINE_FILE_NAME
# from common.logger import init_logging
#
# logger = logging.getLogger(__name__)
#
# VERSION = "0.95"
#
# def processCANFD2FrFile(originalAscFile, inOutputFolder, comMatrixIdentity, valid_first_frame_pattern):
#     fileName = ""
#     t = 0
#     result = re.search("([a-zA-Z0-9_\-]+)\.asc$", originalAscFile)
#     logger.debug("Input line: {}".format(originalAscFile))
#
#
#     if result is not None:
#         fileName = result.group(1)
#     else:
#         logger.debug("Couldn't interpret file name! File name = '{}'".format(originalAscFile))
#
#     tmpFolder = "{}\{}".format(inOutputFolder, TEMP_FOLDER)
#
#     convertedAscFile = "{}\{}{}.asc".format(tmpFolder, PRE_TAG_TEMP_ASC_FILE, fileName)
#     print(convertedAscFile)
#
#     originalAscFileWithPath = "{}\{}".format(tmpFolder, originalAscFile)
#     logger.info("convertedAscFile is {}&orignalAscFiel is {}".format(convertedAscFile, originalAscFileWithPath))
#
#     result = re.search("([a-zA-Z0-9_\-]+\.asc)$", originalAscFile)
#     if result is None:
#         raise FileNotFoundError("Couldn't interpret file name! File name = '{}'".format(originalAscFile))
#
#     if not os.path.isfile(convertedAscFile):
#         raise FileExistsError("Converted file path {} does not exist. Exiting...".format(convertedAscFile))
#
#     tmpFolder = "{}\{}".format(inOutputFolder, TEMP_FOLDER)
#     # outputFilename = outputFolder + "\" + convertedAscFile + "_" + comMatrixIdentity + ".asc"'
#     outputFilename = "{}\{}_{}.asc".format(tmpFolder, fileName, comMatrixIdentity)
#     # logger.debug("Output file name: '{}'".format(outputFilename))
#     outputFP = open(outputFilename, "w")
#     # if outputFP is None:
#     #     raise CreateFileError("Couldn't create file {}!".format(outputFilename))
#
#
#     validData = []
#
#     intro = ["date Fri Aug 31 11:59:41.217 pm 2018\n",
#              "base hex  timestamps absolute\n",
#              "no internal events logged\n",
#              "// version 10.0.1\n",
#              "Begin TriggerBlock Fri Aug 31 11:59:41.662 pm 2018\n"
#              "   0.000000 Start of measurement\n"]
#
#     for row in intro:
#         validData.append(row)
#
#     ori_pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) " "Start of measurement")
#     startTime = 0
#     with open(originalAscFileWithPath, 'r')as fp:
#         for line in fp:
#             result = re.search(ori_pattern, line)
#             if result is not None:
#                 startTime = float(result.group(1))
#
#     frames_result = []
#     pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) Fr RMSG([ ]+[0-9a-zA-Z]+){4}[ ]+([0-5]+)[ ]+([0-9a-zA-Z]+) ")
#     with open(convertedAscFile, 'r') as fp:
#         for line in fp:
#             result = re.search(pattern, line)
#
#             if result is not None:
#                 timestamp = startTime + float(result.group(1))
#
#                 # print(timestamp)
#                 # print(str(timestamp))
#                 thus_str = line.replace(result.group(1), "%.6f"%timestamp)
#                 # logger.info(
#                 #     "startTime: {0}: timestamp:{1},floatTime: {2}".format(startTime, thus_str, float(result.group(1))))
#                 # print("thus_str:", thus_str)
#                 frames_result.append(thus_str)
#     validData.extend(frames_result)
#     endtriger = ["End TriggerBlock\n"]
#     validData.extend(endtriger)
#     with open(outputFilename, 'w+') as fp:
#         for i in validData:
#             fp.write(i)
#
#
#     logFolder = "{}\{}".format(inOutputFolder, LOG_FOLDER)
#     inputFile = "{}\{}_{}.asc".format(tmpFolder, fileName, comMatrixIdentity)
#     ret = subprocess.call([ASC2ADTF, "--log-path", logFolder, "--output-dir", tmpFolder, "--input-file", inputFile])
#
#     datFileName = "{}_{}.dat".format(fileName, comMatrixIdentity)
#
#     return [ret, datFileName]
#
# # processCANFD2FrFile("SVS416A0DC0009_SE-YKW104_20180228_222005_FlexRay2.asc", "E:\\GEEA2\\Temp", "SP_GEEA","^[ ]+[0-9]+\.[0-9]{6} AsdmFLC_FlexrayFr[0-9]+")
# string ="    0.640448 Fr RMSG  0 11 1 1 4 0 Tx 0 84002 5  20  222 AsdmFLC_FlexrayFr03 40 40 00 9c 80 00 00 00 00 30 00 00 00 00 00 00 00 00 00 00 00 02 bc 00 00 00 00 00 00 5d c0 5d c0 5d c0 70 00 00 00 00 00 00 00 00 00 00 00 01 02 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 0  0  0"
# pattern ="^//[ ]+[0-9]+\.[0-9]{6} (AsdmFLC_FlexrayFr): [0-9]+"
import re
data="9273.899600 1  Statistic: D 0 R 0 XD 0 XR 0 E 0 O 0 B 0.00%"
pattern = "(.*)Statistic"
patter = re.match(pattern,data).group(0)
print(patter)
