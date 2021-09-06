import re
import os
import logging 

from collections import defaultdict

from .file_engineer import *


def extract_metadata(metadata):
    """
    """
    loc_index = metadata.find("current line: ")
    instr = metadata[len("current instruction: "):loc_index]
    loc = metadata[loc_index+len("current line: "):]
    return instr, loc    


def framac_output_split(framac_out, params):
    """
    First step in parsing Frama-C value analysis output
    """
    pretty_value_sets = defaultdict(set)    

    _, prettyvsa_output = framac_out.split("START PRETTY VSA")
    # last item is not part of the result
    # EX: "\nmake: Leaving directory '/tmp/zfp-0.16860656542979857'"
    prettyvsa_output = prettyvsa_output.split("----------")[:-1] 

    for value_sets_at_loc in prettyvsa_output:
        value_sets_nonewline = value_sets_at_loc.replace("\n", "")
        end_of_metadata_index = value_sets_nonewline.find("END_OF_METADATA")
        # metadata contains instruction, filename, and line number
        metadata = value_sets_nonewline[:end_of_metadata_index]
        # value set from Frama-C script print value set to stdout in the format of a Python list
        value_sets = eval(value_sets_nonewline[end_of_metadata_index+len("END_OF_METADATA"):])

        # list is empty (no value set)
        if not value_sets:
            continue

        instr, loc = extract_metadata(metadata)        
        print("CURRENT INSTRUCTION:", instr)

        # parse content of value_sets
        for vs in value_sets:
            values = list()
            var_name, _set = vs.split(":")

            # only want value sets of variable that is used in current instruction
            if var_name not in instr:
                continue

            match _set.split():
                case ["{{", "}}"]:
                    continue
                case ["{{", "NULL", "->", "[--..--]", "}}"]:
                    continue
                case ["{{", _, "->", *to_extract, "}}"]:
                    to_extract = "".join(to_extract) 

                    # filter out floating point range
                    match list(to_extract):
                        case ["{", *_, ".", "}"] | ["[", *_, ".", "]"]:
                            continue
                    # filter out formats that do not give explicit, manageable intervals
                    # documents for all possible value set formats can be found in 
                    # "3.1.3 Interpreting the variation domains" of the Frama-C EVA manual
                    if "inf" in to_extract:
                        continue
                    if "&" in to_extract:
                        continue
                    if "NaN" in to_extract:
                        continue
                    
                    match list(to_extract):
                        case ["{", *_, "}"]:  # EX: {1; 2; 3}
                            pretty_value_sets[loc+":"+var_name].update(eval(to_extract.replace(";", ",")))
                        case ["[", *_range, "]"]:
                            _range = "".join(_range)
                            start, end = _range.split("..")
                            if int(end)-int(start) > params.value_set_limit:
                                continue
                            pretty_value_sets[loc+":"+var_name].update(list(range(int(start), int(end)+1)))
                        case ["[", *_range, "]", ",", remainder, "%", divisor]:
                            _range = "".join(_range)
                            start, end = _range.split("..")
                            if int(end)-int(start) > params.value_set_limit:
                                continue
                            pretty_value_sets[loc+":"+var_name].update([i for i in list(range(int(start), int(end)+1)) if i%int(divisor)==int(remainder)])
                        case _:
                            print("NOT HANDLED: CONTACT DEVELOPER")
                case _:
                    print("NOT HANDLED: CONTACT DEVELOPER")

    return pretty_value_sets
