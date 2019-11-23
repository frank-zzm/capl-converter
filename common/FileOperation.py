import os

class FileOP():

    def del_file(self,path):
        if os.path.isfile(path):
            os.remove(path)
        else:
            for i in os.listdir(path):
                path_file = os.path.join(path, i) #// 取文件绝对路径
                if os.path.isfile(path_file):
                    os.remove(path_file)
                else:
                    self.del_file(path_file)
