import os
import subprocess
import unittest
import tempfile

current_dir = os.path.dirname(os.path.realpath(__file__))

class TestSplittingInputFile(unittest.TestCase):

    def test_resim2910_conversion(self):
        reference_dir = "./test/data/splitReference/"
        script = "./Tools/GVP-11882/splitInputFile.py"
        input_file = "./test/data/SplitTestInputList.txt"
        splitted_file_size = 5

        with tempfile.TemporaryDirectory(dir=current_dir) as output_dir:
            split_cmd = "py {} -n {} -i {} -o {}".format(script, splitted_file_size, input_file, output_dir)
            self.assertEqual(subprocess.call(split_cmd, shell=False), 0, "Split.py exited with error code")
            self.verify_split(reference_dir, output_dir)

    def verify_file_content(self, reference_filename, converted_filename):
        with open(reference_filename) as ref_file, open(converted_filename) as conv_file:
            ref_lines = ref_file.readlines()
            conv_lines = conv_file.readlines()
            self.assertEqual(len(ref_lines), len(conv_lines), "The number of lines in output file is incorrect")
            for conv_line, ref_line in zip(conv_lines, ref_lines):
                self.assertEqual(ref_line, conv_line, "Output file content is incorrect")

    def verify_split(self, reference_dir, converted_dir):
        # Check if the expected directory was created by the script
        self.assertTrue(os.path.isdir(converted_dir), "Output directory was not created!")
        # Compare the number of created output files
        list_ref = os.listdir(reference_dir)
        list_conv = os.listdir(converted_dir)
        self.assertEqual(len(list_ref), len(list_conv), "Incorrect number of created output files")

        for inx, value in enumerate(list_ref):
            # Compare names of the created files
            self.assertEqual(value, list_conv[inx], "Output file has incorrect name")
            converted_filename = os.path.join(converted_dir, list_conv[inx])
            reference_filename = os.path.join(reference_dir, value)
            if_same = self.verify_file_content(reference_filename, converted_filename)


if __name__ == "__main__":
    unittest.main()