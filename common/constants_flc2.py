"""Constants unique to FLC2."""
import logging

logger = logging.getLogger(__name__)
logger.info("Importing shared variables for FLC2")

CAPL_CONFIG_FILE = 'Configuration_FLC2_resim_CANoe_v10.cfg'
VALID_FIRST_FRAME_PATTERN = r"^//[ ]+[0-9]+\.[0-9]{6} (AsdmMid2FlxTimeSynchFr): [0-9]+"
