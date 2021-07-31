import pdb

import logging
import subprocess

from collections import defaultdict


def extract_funcsend(llvm_output):
    """
    Retrieve function starting and ending line and store result in a dictionary
    """
    result = defaultdict(int)

    # Remove warning msg in beginning of pass and do proper filtering
    # Warning msg is always the same 5 lines
    rm_template = [l.rstrip("\r\n") for l in llvm_output.split("\n")[5:]]
    rm_template = list(set(rm_template))

    for o in rm_template:
        func_name, ending_line, starting_line = o.split(":")
        result[func_name] = (starting_line, ending_line)  # key is function name. value is line number so it's an int
    return result


def extract_findvars(llvm_output):
    """
    Retrieve variables at line/function and store result in a dictionary
    """
    result = defaultdict(list)

    # Remove warning msg in beginning of pass and do proper filtering
    # Warning msg is always the same 5 lines
    rm_template = [l.rstrip("\r\n") for l in llvm_output.split("\n")[5:]]
    rm_template = list(set(rm_template))

    for o in rm_template:
        line, var, func_name = o.split(":")  # line, vars
        result[line+":"+func_name].append(var)  # key is line number. value is VSA so it's a list
    return result


def filter_nonexistent_vars(src_code, variables):
    """
    LLVM pass is not perfect. Sometimes it output variables with random number appended to it (ex: kilo)
    """
    filtered = defaultdict(list)
    for loc, _vars in variables.items():  # loc = line:function_name
        line = loc.split(":")[0]
        possible_injection_line = int(line) - 1
        for v in _vars:
            if v in src_code[possible_injection_line]:
                filtered[loc].append(v)
    return filtered


def get_funcs_end(src_code, funcs_possible_end):
    """
    Retrieve function starting and ending line and store result in a dictionary
    """
    funcs_end = dict()
    for func_name in funcs_possible_end.keys():
        starting_line, ending_line = funcs_possible_end[func_name]
        possible_injection_line = int(ending_line) - 1
        while True:
            # -2 is line prior to where llvm thinks the function ends
            if "return " in src_code[possible_injection_line-1]:
                possible_injection_line -= 1
            else: 
                funcs_end[func_name] = (starting_line, possible_injection_line)
                break
    return funcs_end
 
