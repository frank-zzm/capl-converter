import os
import logging
import re
import binascii
from typing import List, TextIO
from common.version import get_version

logger = logging.getLogger(__name__)

data_start_tag = "// Begin MetadataBlock\n"
data_end_tag = "// End MetadataBlock\n"


class AMFError(Exception):
    pass


class Metadata:
    def __init__(self,
                 metadata_identifier,
                 magic="AMF1\n",
                 length="0x00 0x00 0x00 0x00\n",
                 metadata_info=None):
        self.metadata_identifier = metadata_identifier
        self.magic = magic
        self.length = length
        if metadata_info is None:
            self.metadata_info = []
        else:
            self.metadata_info = metadata_info
        self.crc = self.calculate_crc32()

    def calculate_crc32(self):
        crc_metadata = [self.magic] + [self.length] + self.metadata_info
        prev = 0
        for line in crc_metadata:
            prev = binascii.crc32(bytearray(line, 'utf-8'), prev)
        crc = self.hex_record("%x" % (prev & 0xFFFFFFFF))
        return crc

    def write(self, o_file: TextIO):
        comment_prefix = "// "
        o_file.write(comment_prefix + self.metadata_identifier)
        o_file.write(comment_prefix + self.magic)
        o_file.write(comment_prefix + self.length)
        for info in self.metadata_info:
            o_file.write(comment_prefix + info)
        o_file.write(comment_prefix + self.crc)

    @staticmethod
    def parse_hex_value(hex_str: str):
        hex_pattern = r"0x([A-Fa-f0-9]{2}) 0x([A-Fa-f0-9]{2}) 0x([A-Fa-f0-9]{2}) 0x([A-Fa-f0-9]{2})"
        matched_line = re.match(hex_pattern, hex_str, re.DOTALL)
        if not matched_line:
            raise AMFError("ParseHexValue: regex match failed ")

        value = int('{}{}{}{}'.format(matched_line.group(4),
                                      matched_line.group(3),
                                      matched_line.group(2),
                                      matched_line.group(1)),
                    16)
        return value

    @staticmethod
    def hex_record(hex_value: str):
        hex_value = hex_value.rjust(8, '0')
        hex_pattern = r"([A-Fa-f0-9]{2})([A-Fa-f0-9]{2})([A-Fa-f0-9]{2})([A-Fa-f0-9]{2})"
        matched_hex = re.match(hex_pattern, hex_value, re.DOTALL)
        if not matched_hex:
            raise AMFError("Hex record: regex match failed ")

        return "0x{} 0x{} 0x{} 0x{}\n".format(matched_hex.group(4),
                                              matched_hex.group(3),
                                              matched_hex.group(2),
                                              matched_hex.group(1))


class FileMetadata(Metadata):
    def __init__(self,
                 magic="AMF1\n",
                 length="0x00 0x00 0x00 0x00\n",
                 metadata_info=None):
        Metadata.__init__(self, "metadata File\n", magic, length, metadata_info)

    def get_revision_number(self):
        revision_number = 0
        for trace_data in self.metadata_info:
            trace_info_pattern = "TracingInformation/Revision/([0-9]+)/.*"
            matched_line = re.match(trace_info_pattern, trace_data, re.DOTALL)
            if matched_line:
                current_revision = int(matched_line.group(1))
                revision_number = current_revision if revision_number < current_revision else revision_number
        return revision_number + 1

    def add_capl_trace_info_to_metadata(self, folder_name: str, revision_number: int):
        curr_len = self.parse_hex_value(self.length)
        trace_info_script_version = self.process_versions(folder_name, revision_number, 'CaplScriptVersion')
        self.metadata_info.append(trace_info_script_version)
        curr_len += len(trace_info_script_version)
        trace_info_canoe_version = self.process_versions(folder_name, revision_number, 'CanoeVersion')
        self.metadata_info.append(trace_info_canoe_version)
        curr_len += len(trace_info_canoe_version)

        git_version = get_version("CAPLconverter")
        trace_info_version = f"TracingInformation/Revision/{revision_number}/CaplConverter/Version {git_version}\n"
        self.metadata_info.append(trace_info_version)
        curr_len += len(trace_info_version)

        self.length = self.hex_record("%x" % curr_len)
        self.crc = self.calculate_crc32()

    def prepare_file_metadata(self, folder_name: str):
        revision_number = self.get_revision_number()
        self.add_capl_trace_info_to_metadata(folder_name, revision_number)

    @staticmethod
    def process_versions(folder_name: str, revision_number: int, version: str):
        version_file_path = os.path.join(folder_name, version + '.txt')
        if not os.path.isfile(version_file_path):
            raise AMFError("Version file {} doesn't exist".format(version_file_path))
        with open(version_file_path) as version_file:
            line = version_file.readline()
            version_str = "ScriptVersion" if version == "CaplScriptVersion" else version
            trace_info = "TracingInformation/Revision/{}/CaplConverter/{} {}\n".format(revision_number,
                                                                                       version_str,
                                                                                       line)
        return trace_info


MetadataList = List[Metadata]


def is_file_level_metadata(line: str):
    metadata_file_pattern = "metadata File"
    matched_metadata_line = re.search(metadata_file_pattern, line, re.DOTALL)
    return True if matched_metadata_line else False


def remove_comment_prefix(line: str):
    if line.startswith('// '):
        line = line[3:]
    return line


def get_metadata_info(input_file: TextIO, size: int, metadata_info: List[str]):
    while size > 0:
        line = input_file.readline()
        metadata_pattern = "// metadata"
        if not line or re.search(data_end_tag, line, re.DOTALL) or re.match(metadata_pattern, line, re.DOTALL):
            # The end of the metadata or the next metadata is reached
            raise AMFError("AMF Metadata size mismatch.")
        line = remove_comment_prefix(line)
        metadata_info.append(line)
        if len(line) > size:
            raise AMFError("AMF Metadata size mismatch.")
        size -= len(line)


def add_metadata(i_file: TextIO, amf_metadata: MetadataList):
    metadata_pattern = "// metadata"

    line = i_file.readline()
    if re.search(data_end_tag, line, re.DOTALL):
        # The end of the metadata is reached
        return False
    if not line:
        raise AMFError("End MetadataBlock is missing!")
    if not re.match(metadata_pattern, line, re.DOTALL):
        raise AMFError("{}: Metadata is missing!".format(line.strip()))

    metadata_id_line = remove_comment_prefix(line)

    line = i_file.readline()
    amf_pattern = "// AMF1"
    matched_magic_line = re.match(amf_pattern, line, re.DOTALL)
    if not matched_magic_line:
        raise AMFError("{}: Magic and AMF version are missing.".format(metadata_id_line.strip()))
    amf_line = remove_comment_prefix(line)

    length_line = remove_comment_prefix(i_file.readline())
    metadata_info: List[str] = []

    amf_length = Metadata.parse_hex_value(length_line)
    get_metadata_info(i_file, amf_length, metadata_info)
    crc_line = i_file.readline()
    metadata = Metadata(metadata_id_line, amf_line, length_line, metadata_info)

    if metadata.crc.lower() != remove_comment_prefix(crc_line.lower()):
        raise AMFError("{}: Failed CRC check!".format(metadata_id_line.strip()))

    if is_file_level_metadata(metadata_id_line):
        metadata.__class__ = FileMetadata

    amf_metadata.append(metadata)
    return True


def get_metadata_list(file_path: str, metadata_list: MetadataList):
    if not os.path.isfile(file_path):
        raise AMFError("File {} does not exist.".format(file_path))

    with open(file_path) as i_file:
        # Find the metadata start tag which represents the AMF beginning right after
        line = i_file.readline()
        while line:
            if re.search(data_start_tag, line, re.DOTALL):
                # Metadata block is found
                break
            if re.search(data_end_tag, line, re.DOTALL):
                # 'End MetadataBlock' is found, but 'Begin MetadataBlock' is missing
                raise AMFError("'Begin MetadataBlock' is missing.")
            line = i_file.readline()

        if not line:
            # Input file doesn't contain metadata
            # Add file level metadata as a first metadata in the metadata list
            file_metadata = FileMetadata()
            metadata_list.insert(0, file_metadata)
            return

        while add_metadata(i_file, metadata_list):
            pass

    if metadata_list and not isinstance(metadata_list[0], FileMetadata):
        raise AMFError("File level metadata should be the first element of the metadata list.")

    if not metadata_list:
        # Input file contains 'Begin MetadataBlock', 'End MetadataBlock', but metadata is missing
        raise AMFError("Amf is missing.")


def save_amf_to_file(amf: MetadataList, file_path: str):
    # Save metadata which represents AMF to the appropriate file
    with open(file_path, "a") as o_file:
        o_file.write(data_start_tag)
        for metadata in amf:
            metadata.write(o_file)
        o_file.write(data_end_tag)


def add_capl_tracing_info(folder_name: str, metadata_list: MetadataList):
    # Add tracing information about CaplConverter and Canoe version to the file level metadata
    file_metadata = metadata_list[0]
    if isinstance(file_metadata, FileMetadata):
        file_metadata.prepare_file_metadata(folder_name)
    else:
        raise AMFError("File level metadata is missing.")
