import re

pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) "
                     "Fr RMSG([ ]+[0-9a-zA-Z]+){4}[ ]+([0-9a-zA-Z]+)[ ]+([0-9a-zA-Z]+) "
                     "[R|T]x([ ]+[0-9a-zA-Z]+){5} ([0-9a-zA-Z]+)")
pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) Fr RMSG([ ]+[0-9a-zA-Z]+){4}[ ]+([0-5]+)[ ]+([0-9a-zA-Z]+) ")
original_file=r"C:\Users\Frank.zhang\Desktop\AEB_project\Geea2.0\Data\CORE_Data\SVS416A0DC0009_SE-YKW104_20180228_185010_CORE_CAN1.asc"
path=r"C:\Users\Frank.zhang\Desktop\AEB_project\Geea2.0\Data\CORE_Data\SVS416A0DC0009_SE-YKW104_20180228_185010_CORE_frlexray_trail.asc"
dest_path= r"C:\Users\Frank.zhang\Desktop\AEB_project\Geea2.0\Data\CORE_Data\SVS416A0DC0009_SE-YKW104_20180228_185010_CORE_frlexray_test.asc"
# line=   '   0.450082 Fr RMSG  0 10 1 1 6 1a Tx 0 84c06 5  20  1c1 AsdmFLC_FlexrayFr00 40 40 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 ff 50 00 00 00 00 09 06 40 ff 50 00 00 00 00 00 00 00 00 00 00 5d c0 5d c0 5d c0 00 00 00 0  0  0'
# line = '   0.450448 Fr RMSG  0 10 1 1 4 1a Tx 0 84c02 5  20  222 AsdmFLC_FlexrayFr03 40 40 00 9c 80 00 00 00 00 30 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 50 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 0  0  0'
ori_pattern = re.compile("^[ ]+([0-9]+\.[0-9]{6}) " "Start of measurement")

startTime=0
with open (original_file,'r')as fp:
    for line in fp:
        result=re.search(ori_pattern ,line)
        if result is not None:
            startTime=float(result.group(1))
string="30.195448"
value= float(string)
print(value)
validData = []
dest_result= []
intro = ["date Fri Aug 31 11:59:41.217 pm 2018\n",
             "base hex  timestamps absolute\n",
             "no internal events logged\n",
             "// version 10.0.1\n",
             "Begin TriggerBlock Fri Aug 31 11:59:41.662 pm 2018\n"
             "   0.000000 Start of measurement\n"]

for row in intro:
    validData.append(row)
with open (path,'r') as fp:
    for line in fp:
        result = re.search(pattern,line)

        if result is not None:
            timestamp  = startTime +float(result.group(1))
            # print(timestamp)
            # print(str(timestamp))
            thus_str= line.replace(result.group(1),str(timestamp))
            # print("thus_str:", thus_str)
            dest_result .append(thus_str)
            # print("orig_str:", line)
            # print(result.group(1)+result.group(2)+result.group(3)+result.group(4) )
            # print(result)


validData.extend(dest_result)
endtriger = ["End TriggerBlock\n"]
validData.extend(endtriger)
# for i in validData:
#     print(i)
with open(dest_path,'w+') as fp:
    for i in validData:
        fp.write(i)


# 能够将数据转为Flexray，且可以转换为ADTF，question:begin tregger时间和真实的时间戳之间的关系是怎样的