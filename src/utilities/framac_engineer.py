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

    _, prettyvsa_curfuncs_output = framac_out.split("START PRETTY VSA (ZFP)")
    prettyvsa_output, curfuncs_output = prettyvsa_curfuncs_output.split("FUNCTIONS IN SOURCE (ZFP)")
    curfuncs = curfuncs_output.split()
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

        # parse content of value_sets
        for vs in value_sets:
            var_name, _set = vs.split(":")
            is_bool = False

            # only want value sets of variable that is used in current instruction
            if var_name not in instr:
                continue
            if var_name == "__retres":
                # return value statement
                continue
            if "tmp_" in var_name:
                # Frama-C internal variable to keep track of intermediate values
                # Variable does not exist in original source. Unless developer 
                # names the variable to start with "tmp_", in that case cannot
                # differentiate so ignore to be safe
                # EX: return value from rand()
                continue
            if any([func for func in curfuncs if var_name.startswith(func+"_")]):
                # Boolean variable will be outputted by Frama-C with its function name prepended
                # Boolean variable and the function name is separated by a '_'
                is_bool = True

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

                    # Frama-C represents Boolean variable differently. However, when inserted back
                    # into source, we need the original variable name. So here we reconstruct the 
                    # original variable name
                    if is_bool:
                        underscore_index = var_name.find("_")
                        var_name = var_name[underscore_index+1:]
                    
                    match list(to_extract):
                        case ["{", *_, "}"]:  # EX: {1; 2; 3}
                            pretty_value_sets[loc+":"+var_name].update(
                                eval(to_extract.replace(";", ","))
                            )
                        case ["[", *_range, "]"]:  # EX: [1..256]
                            _range = "".join(_range)
                            start, end = _range.split("..")
                            if int(end)-int(start) > params.value_set_limit:
                                continue
                            pretty_value_sets[loc+":"+var_name].update(
                                list(range(int(start), int(end)+1))
                            )
                        case ["[", *_range, "]", ",", remainder, "%", divisor]:  # EX: [1..245],0%2
                            _range = "".join(_range)
                            start, end = _range.split("..")
                            if int(end)-int(start) > params.value_set_limit:
                                continue
                            pretty_value_sets[loc+":"+var_name].update(
                                [i for i in list(range(int(start), int(end)+1)) if i%int(divisor)==int(remainder)]
                            )
                        case _:
                            raise SystemExit("Error in parsing Frama-C script's output")
                case _:
                    raise SystemExit("Error in parsing Frama-C script's output")

    return pretty_value_sets
