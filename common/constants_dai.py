"""Constants unique to DAIMLER."""
import logging

logger = logging.getLogger(__name__)
logger.info("Importing shared variables for Daimler")

CAPL_CONFIG_FILE = 'Configuration_DAI_to_FLC2_CANoe_v1.cfg'
VALID_FIRST_FRAME_PATTERN = "^//[ ]+[0-9]+\.[0-9]{6} (AsdmMid2FlxFr01)\: [0-9]+"
