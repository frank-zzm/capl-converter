import json
import logging
from argparse import ArgumentParser

logger = logging.getLogger(__name__)


class JSONParseError(Exception):
    pass


def get_flexray_streams(filepath):
    with open(filepath, 'r') as f:
        data = json.load(f)

    streams = {}
    try:
        # Stream index / bus specification
        streams.update({1: data['properties'][0]['bob_FlexRay']})
        streams.update({2: data['properties'][0]['bob_FlexRay2']})
    except KeyError:
        raise JSONParseError("Couldn't parse flexray streams from {}".format(filepath))

    return streams


if __name__ == '__main__':
    parser = ArgumentParser(description='DAT Metadata extraction tool')
    parser.add_argument('path', type=str, help='Path to .DAT file')
    args = parser.parse_args()

    streams = get_flexray_streams(args.path)
    for stream_id, specification in streams.items():
        print("FlexRay{} = {}".format(stream_id, specification))
