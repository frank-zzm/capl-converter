"""Constants unique to geely."""
import logging

logger = logging.getLogger(__name__)
logger.info("Importing shared variables for GEEA2.0")

CAPL_CONFIG_FILE = r"C:\git\capl-converter\Configuration_FLC2_resim_CANoe_SVS_GEEA2_E3U2E4.cfg"# GEEA2.0 config
CAPL_CONFIG_FILE_E3U = r"C:\git\capl-converter\Configuration_FLC2_resim_CANoe_v10_GEEA2_E3U.cfg"
CAPL_CONFIG_FILE_E4 =  r"C:\git\capl-converter\Configuration_FLC2_resim_CANoe_SVS_GEEA2_E4.cfg"
CAPL_CONFIG_FILE_E3U2E4 =  r"C:\git\capl-converter\Configuration_FLC2_resim_CANoe_SVS_GEEA2_E3U2E4.cfg"
CAPL_CONFIG_FILE_Core2E3U = r"C:\git\capl-converter\Configuration_FLC2_resim_CANoe_SVS_GEEA2_core2E3U.cfg"
CAPL_CONFIG_FILE_DAI2E4 = "C:\git\capl-converter\Configuration_FLC2_resim_CANoe_SVS_GEEA2_DAI2E4_SVS.cfg"
# CAPL_CONFIG_FILE = r"C:\git\capl-converter\Configuration_FLC2_resim_CANoe_SVS_GEEA2_core2E3U.cfg" # CORE config
# VALID_FIRST_FRAME_PATTERN = "^//[ ]+[0-9]+\.[0-9]{6} (AsdmMid2FlxTimeSynchFr)\: [0-9]+"
# VALID_FIRST_FRAME_PATTERN = "^//[ ]+[0-9]+\.[0-9]{6} (ASDMFlcFlexTimeSynchFr)\: [0-9]+"   #frank:modified
# test::change the parttern "synchfr"to any receiver signal
VALID_FIRST_FRAME_PATTERN = "^[ ]+[0-9]+\.[0-9]{6} (AsdmFLC_FlexrayFr): [0-9]+"# it is only for _tmp
# VALID_FIRST_FRAME_PATTERN = "^[ ]+[0-9]+\.[0-9]{6} ASDMFlcFlexTimeSynchFr"
VALID_Rx_ASDM2FLC_Frame="^[ ]+([0-9]+\.[0-9]{6}) Fr RMSG([ ]+[0-9a-zA-Z]+){4}[ ]+([0-5]+)[ ]+([0-9a-zA-Z]+) "#for Geely first valid ASDM->FLC data