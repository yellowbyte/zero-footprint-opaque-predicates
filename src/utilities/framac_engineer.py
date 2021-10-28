import logging
import os
import re
from collections import defaultdict


def extract_vars(instr):
    """
    Given a C `instr`, return a list containing all the variable names it uses
    """
    return set(re.findall(r"[a-zA-Z]\w*", instr))


def extract_metadata(metadata):
    """
    Given `metadata` produced from the custom Frama-C script,
    extract the line number and instruction information
    """
    loc_index = metadata.find("current line: ")
    instr = metadata[len("current instruction: "):loc_index]
    loc = metadata[loc_index+len("current line: "):]
    return instr, loc


def framac_output_split(framac_out, ignored_lines, params):
    """
    First step in parsing Frama-C value analysis output
    """
    pretty_value_sets = defaultdict(set)

    prettyvsa_curfuncs_output = framac_out.split("START PRETTY VSA (ZFP)")[-1]
    prettyvsa_output, curfuncs_output = prettyvsa_curfuncs_output.split(
        "FUNCTIONS IN SOURCE (ZFP)"
    )
    curfuncs = curfuncs_output.split()
    # last item is not part of the result
    # EX: "\nmake: Leaving directory '/tmp/zfp-0.16860656542979857'"
    prettyvsa_output = prettyvsa_output.split("----------")[:-1]

    for value_sets_at_loc in prettyvsa_output:
        value_sets_nonewline = value_sets_at_loc.replace("\n", "")
        end_of_metadata_index = value_sets_nonewline.find("END_OF_METADATA")
        # metadata contains instruction, filename, and line number
        metadata = value_sets_nonewline[:end_of_metadata_index]
        # value set from Frama-C script print value set to stdout
        # in the format of a Python list
        try:
            # TODO:
            # may fail. Investigate more since my custom script
            # should print to stdout a formatted python list
            vs_index = end_of_metadata_index+len("END_OF_METADATA")
            value_sets = eval(value_sets_nonewline[vs_index:])
        except:  # noqa
            continue

        # list is empty (no value sets)
        if not value_sets:
            continue

        instr, loc = extract_metadata(metadata)
        var_names = extract_vars(instr)

        # current instruction is a oneliner
        # Oneliner (e.g., one-line if statement, one-line for-loop)
        # will mess up our tool
        # EX loc: 09_loop_for_complex.c:7
        # if int(loc.split(":")[1]) in ignored_lines:
        #    continue
        if loc.split(":")[0] in ignored_lines.keys():
            # current file contains lines that need to be ignored
            if loc.split(":")[1] in ignored_lines[loc.split(":")[0]]:
                # current line needs to be ignored
                continue

        # parse content of value_sets
        for vs in value_sets:
            # content of _set may also contain the char ":"
            var_name, _set = vs.split(":{{")
            _set = "{{" + _set
            is_bool = False

            # only want value sets of variable in current instruction
            if var_name not in var_names:
                continue
            if var_name == "__retres":
                # return value statement
                continue
            if "tmp" in var_name:
                # Frama-C internal variable to keep track of intermediate values
                # Variable does not exist in original source. Unless developer
                # names the variable to start with "tmp" or "tmp_" cannot
                # differentiate so ignore to be safe
                # EX: return value from rand()
                continue
            if any([fun for fun in curfuncs if var_name.startswith(fun+"_")]):
                # Boolean variable will be outputted by Frama-C
                # with its function name prepended
                # Boolean variable and the function name is separated by a '_'
                is_bool = True

            match _set.split():  # noqa
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
                    # filter out formats that do not give manageable intervals
                    # documents for all possible value set formats can be
                    # found in "3.1.3 Interpreting the variation domains" of the
                    # Frama-C EVA manual
                    if "inf" in to_extract:
                        continue
                    if "&" in to_extract:
                        continue
                    if "NaN" in to_extract:
                        continue
                    if "mix of " in to_extract:
                        continue

                    # Frama-C represents Boolean variable differently.
                    # However, when inserted back into source, we need
                    # the original variable name. So here we reconstruct the
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
                        case _ if "," in list(to_extract) and "%" in list(to_extract):  # EX: [1..245],0%20  # noqa
                            # range can be negative
                            # numbers does not have to be single digit
                            range_pattern = r'\[([0-9-]+)\.\.([0-9-]+)\],([0-9]+)%([0-9]+)'  # noqa
                            match = re.search(range_pattern, to_extract)
                            start = match.group(1)
                            end = match.group(2)
                            remainder = match.group(3)
                            divisor = match.group(4)

                            if int(end)-int(start) > params.value_set_limit:
                                continue
                            pretty_value_sets[loc+":"+var_name].update(
                                [i for i in list(range(int(start), int(end)+1))
                                 if i % int(divisor) == int(remainder)]
                            )
                        case _:
                            continue
                case _:
                    continue

    return pretty_value_sets
