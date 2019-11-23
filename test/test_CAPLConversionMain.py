import itertools
import os
import subprocess
import unittest
import tempfile

current_dir = os.path.dirname(os.path.realpath(__file__))
FR_CLIENT_ID_COLUMN_NR = 4
FR_FLAG_COLUMN_NR = 11
DATA_VALID_BIT = 0x02

class TestCaplConversionMain(unittest.TestCase):

    def test_resim2910_conversion(self):
        """
        Run converter on output from CAPLconversionMain.py.
        Verify that it is correct by comparing to REFERENCE_FILE.
        Note: The 12:th column only needs to be equal after applying "and 0x02".

        """
        NEW_CONVERTED_FILE = "ADAS_PHH392_CONT_20180423T110751-20180423T110851_FLC_FlexRay_SPA2910.asc"
        REFERENCE_FILE = "ADAS_PHH392_CONT_20180423T110751-20180423T110851_FLC_FlexRay_SPA2910_ref.asc"

        # Run converter tool
        batch_id = "regressionTest_01"
        filelist = os.path.join(current_dir, "data", "regressionTestFlc2.txt")
        with tempfile.TemporaryDirectory(dir=current_dir) as output_dir:
            # Canoe does not like window slashes
            output_dir = output_dir.replace("\\", "/")
            capl_cmd = "py -3 CAPLconversionMain.py {} {} {} --flc2-resim-2910".format(batch_id, filelist, output_dir)
            self.assertEqual(subprocess.call(capl_cmd, shell=False), 0, "CAPLconversionMain.py exited with error code")

            converted_filename = os.path.join(output_dir, "TempConversionJobs", NEW_CONVERTED_FILE)
            reference_filename = os.path.join(current_dir, "data", REFERENCE_FILE)
            self.verify_converted_file(converted_filename, reference_filename)

    def find_triggerblock_start_line(self, file_obj):
        for line in file_obj:
            if line.lower().startswith("begin triggerblock"):
                return True
        return False

    def compare_flexray_asc_lines(self, line1, line2):
        line1_elements = line1.split()
        line2_elements = line2.split()
        self.assertEqual(len(line1_elements), len(line2_elements))
        for column_nr, (e1, e2) in enumerate(zip(line1_elements, line2_elements)):
            if (column_nr == FR_FLAG_COLUMN_NR):
                modded_e1 = int(e1, 16) & DATA_VALID_BIT
                modded_e2 = int(e2, 16) & DATA_VALID_BIT
                self.assertEqual(modded_e1, modded_e2)
            elif (column_nr == FR_CLIENT_ID_COLUMN_NR):
                # Ignore this column, could differ for different installation of CANoe and has nothing
                # to do with FlexRay data.
                None
            else:
                self.assertEqual(e1, e2, "{}\n{}".format(line1, line2))

    def verify_converted_file(self, converted_filename, reference_filename):
        """
        :param converted_filename: File to verify.
        :return: True if file is correctly converted, otherwise False.
        """
        with open(reference_filename) as ref_file, open(converted_filename) as conv_file:
            # Find and forward file object to "Begin Triggerblock" line
            self.assertTrue(self.find_triggerblock_start_line(ref_file))
            self.assertTrue(self.find_triggerblock_start_line(conv_file))

            ref_line = ref_file.readline()
            conv_line = conv_file.readline()
            while ref_line != "" and conv_line != "":
                # This check is needed to verify that they contain the same amount of flexray packets.
                # Otherwise the converted files could be missing a packet and still pass
                if ref_line.lower().startswith("end triggerblock"):
                    self.assertTrue(conv_line.lower().startswith("end triggerblock"))
                    break
                elif conv_line.lower().startswith("end triggerblock"):
                    self.assertTrue(ref_line.lower().startswith("end triggerblock"))
                    break

                self.compare_flexray_asc_lines(ref_line, conv_line)
                ref_line = ref_file.readline()
                conv_line = conv_file.readline()


if __name__ == "__main__":
    # Note this needs to be run from repo-root because CAPLconversionMain.py requires it
    unittest.main()