import os
from json import JSONDecodeError
from unittest import TestCase
from unittest.mock import patch, mock_open

from common import datparser
from common.datparser import JSONParseError


class TestDatParser(TestCase):

    def test_extract_flexray_streams(self):
        json_file = os.path.join('..', 'data', 'SVS416A0DC0002_SE-PGA454_20180125_095933.json')
        expected = {
            1: 'SMPC_STAR_2_3_V1_2016_Ecu_Details_Extract_2017_05a',
            2: '213_238_257_CHASSIS_FlexRay_2016_42a',
        }

        actual = datparser.get_flexray_streams(json_file)

        self.assertEqual(expected, actual)

    def test_missing_bob_flexray2_field_in_json(self):
        json_data = """
{
  "properties": [{
    "bob_FlexRay": "SMPC_STAR_2_3_V1_2016_Ecu_Details_Extract_2017_05a"
  }]
}
"""
        with patch("builtins.open", mock_open(read_data=json_data)):
            with self.assertRaises(JSONParseError):
                datparser.get_flexray_streams("mock_file")

    def test_invalid_json(self):
        json_data = '{ "property": 1'  # Missing closing block

        with patch("builtins.open", mock_open(read_data=json_data)):
            with self.assertRaises(JSONDecodeError):
                datparser.get_flexray_streams("mock_path")
