import re
import os
import logging 

import pdb


from .file_engineer import *


def get_func_value_sets(value_sets, cur_func, func_vars, funcs_info, params):
    """
    Parse value analysis' default result
    """
    for cur_var in func_vars:  # variables VSA output from Frama-C
        # First level filter            
        if any([cur_var.lstrip().startswith(func_name+"_") for func_name in funcs_info.keys()]):
            # Frama-C is a bit weird in that it will identify value set for a subroutine's local variables
            # in the subroutine's parent function. Value set identified this way have their variable name
            # starts with the subroutine's name and we ignore them since the variable is out of scope
            struct_name = "zfp-none"
            continue
        # Each cur_var is a potential value set of a variable
        if "∈" not in cur_var:
            continue
        var_name, values = cur_var.split("∈")
        var_name = var_name.lstrip().rstrip()
        values = values.lstrip().rstrip()

        if any([v in var_name for v in params.framac_vars]):
            # Ignores Frama-C specific variables. They do not exist in original source
            struct_name = "zfp-none"
            continue
        
        # Identify if var_name is start of a struct
        if "[" in var_name and not var_name.startswith("{") and not var_name.startswith(".") and not var_name.startswith("["):
            # EX: t[0].type
            struct_name = var_name[:var_name.index("[")]
        elif "{" in var_name and not var_name.startswith("{") and not var_name.startswith(".") and not var_name.startswith("["):
            # EX: p{.pos; .toknext}
            struct_name = var_name[:var_name.index("{")]
        elif "." in var_name and not var_name.startswith("{") and not var_name.startswith(".") and not var_name.startswith("["):
            # EX: p.pos
            struct_name = var_name[:var_name.index(".")]

        # the current field or variable has NULL value or memory pointer
        if "NULL" in values:
            continue
        if "&" in values:
            # value set has to do with pointers
            # non-trivial to retrieve
            continue

        # Identify if var_name is an index and add struct name to it if it is
        if var_name.startswith("[") or var_name.startswith("."):
            if struct_name == "zfp-none":
                 # __fc_fds[0..1] ∈ [--..--]
                 #         [2..1023] ∈ {0}       <- current item
                 # ^ __fc_fds line is already skipped
                continue
            # EX: [1].type
            # EX: .toknext
            var_name = struct_name+var_name

        # Identify if var_name contains multiple fields
        # EX: p{.pos; .toknext}
        if "{" in var_name:
            var_name_base = var_name[:var_name.index("{")]
            if not var_name_base:
                var_name_list = [struct_name+v.lstrip() for v in var_name[var_name.index("{")+1:-1].split(";")]
            else:
                var_name_list = [var_name_base+v.lstrip() for v in var_name[var_name.index("{")+1:-1].split(";")]
        else:
            var_name_list = [var_name]

        var_name_list_all = list()
        for v in var_name_list:
            if ".." in v:
                # if multiple braces with ".." just skip. (simplify code for less invariants)
                left_dot = v.find("..")
                right_dot = v.rfind("..")
                if left_dot != right_dot:
                    continue
                # if more than two braces, just skip. (simplify code for less invariants)
                if v.count("[") > 2:
                    continue
                # if multiple braces, figure out which braces have the ".."
                left_side_brace = v.find("[")
                right_side_brace = v.rfind("[")
                if abs(left_dot-left_side_brace) <= abs(left_dot-right_side_brace):
                    # left brace is closer. Or that only one braces
                    left_brace = left_side_brace
                    right_brace =  v.find("]")      
                else:
                    left_brace = right_side_brace
                    right_brace = v.rfind("]")      

                var_name_range = v[left_brace+1:right_brace]
                var_name_base = v[:left_brace]
                start_range, end_range = var_name_range.split("..")

                if int(end_range)-int(start_range) > params.value_set_limit:
                    # too many variables created. Process will be killed
                    continue
                for i in range(int(start_range), int(end_range)+1):
                    var_name_list_all.append(var_name_base+"["+str(i)+"]")                                           
            else:
                var_name_list_all.append(v)

        # Extract list of values
        # Create a list of values from values string
        values_incorrect = False
        if not values:
            # values empty
            #continue
            values_incorrect = True
        elif "{" in values:
            value_set = extract_vsa_discrete(values[1:-1])
        elif "[" in values:
            value_set = extract_vsa_range(values[1:-1], params.value_set_limit)
            if not value_set:
                # Empty value_set 
                #continue
                values_incorrect = True
        else:
            values_incorrect = True
        
        for var in var_name_list_all:
            # make sure variable type exists in function due to Frama-C's percularity
            # Frama-C uses "." to access pointer even though in code it is "->"
            if "." in var and ".." not in var: 
                # make sure "." access type exists in code 
                var_base = var[:var.index(".")]
                var_item = var[var.index(".")+1:]
                if var_base+"." not in funcs_info[cur_func][3]:
                    var = var_base+"->"+var_item

            # make sure variable exists in function.
            # NOTE: May not exist if pass-by-addr since Frama-C will identify it as part of the func when it 
            # it actually part of the parent func
            var_base_index = re.search(r'\W+', var) 
            if var_base_index:
                var_base_index = var_base_index.start()
                var_base = var[0:var_base_index] 
            else:
                var_base = var
            if var_base not in funcs_info[cur_func][3]:
                continue

            loc_info = funcs_info[cur_func][2]+":"+str(funcs_info[cur_func][1])+":"+var
            if values_incorrect: 
                value_sets.pop(loc_info, None)
                continue
            value_sets[loc_info].update(set(value_set))   


def get_macro_info(cur_dir, l):
    """
    Parse value analysis macro result for a variable if it is a macro result
    """
    FRAMAC_MACRO = "Frama_C_show_each_"
    # Each line is potentially a Frama-C macro result for a variable
    # Get relative filepath and line number
    exp = r"(.+):(\d+): "+FRAMAC_MACRO+"(.+):(.+)"
    match = re.match(exp, l, re.DOTALL)
    if not match:
        return list()
    # The string is the result of a Frama-C macro
    file_subpath = match.group(1)
    filepath = os.path.join(cur_dir,file_subpath)
    loc = match.group(2)
    var_name = match.group(3)
    rest = [l.lstrip().rstrip() for l in match.group(4).split("\n")]
    return (filepath, loc, var_name, rest)


def get_macro_value_sets(value_sets, macro_info, blacklist, params):
    """
    Parse value analysis output from the inserted macros
    """
    filepath, loc, var_name, potential_value_set_info = macro_info
    # Example potential_value_set_info (prior to list comprehension):
    #  .pos ∈ {98}\n                       .toknext ∈ {13}\n                       .toksuper ∈ {-1}\n
    #  {.c_iflag; .c_oflag; .c_cflag} ∈ [--..--] or UNINITIALIZED
    #  {{ &t + {16} }}\n
    #  {6}\n
    # {.pos; .toknext} ∈ {0}\n
    index = str()
    potential_value_set_info = [i for i in potential_value_set_info if i]
    for item in potential_value_set_info:
        if "{{" in item:
            # pointer stuff a no no
            return tuple()
        elif "∈" in item:
            index, values = item.split("∈")
            index = index.lstrip().rstrip()
            values = values.lstrip().rstrip()
        else:
            values = item.lstrip().rstrip()

        if "{" in values:
            value_set = extract_vsa_discrete(values[1:-1])
        else:
            value_set = extract_vsa_range(values[1:-1], params.value_set_limit)

        # Differentiate between normal variable and struct element
        var_info_list = list()
        if index:
            # Differentiate between {.c_iflag; .c_oflag; .c_cflag} and just .flag
            if "{" in index:
                indexes = index[1:-1].split(";")
                for i in indexes:
                    var_info_list.append(filepath+":"+loc+":"+var_name+i) 
            else:
                var_info_list = [filepath+":"+loc+":"+var_name+index]
        else:
            var_info_list = [filepath+":"+loc+":"+var_name]

        # Add each variable (indexed or not) into the value_sets dictionary
        for var_info in var_info_list:
            if var_info in blacklist:
                continue
            if not value_set:
                # value_set will be empty if value_set too large (extract_vsa_range)
                if var_info in value_sets.keys():
                    value_sets.pop(var_info)  
                blacklist.append(var_info)
                continue
            value_sets[var_info].update(set(value_set))
        index = str()


def extract_metadata(metadata):
    """
    """
    loc_index = metadata.find("current line: ")
    instr = metadata[len("current instruction: "):loc_index]
    loc = metadata[loc_index+len("current line: "):]
    return instr, loc    


def framac_output_split(framac_out):
    """
    First step in parsing Frama-C value analysis output
    """
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
        filepath, line_number = loc.split(":")

        # parse content of value_sets
        for vs in value_sets:
            var_name, _set = vs.split(":")
            # TODO: use pattern matching to extract list of values from _set

    return prettyvsa_output


def insert_framac_macros(filepath, src_code, variables):
    """
    Insert Frama-C macros so value analysis can identify more 
    """
    for loc, _vars in variables.items():
        line, func_name = loc.split(":")
        uniq_vars = list(set(_vars))
        for var in uniq_vars:
            if "malloc" in src_code[int(line)-1]:
                continue
            if src_code[int(line)-1].endswith(";") and "return " not in src_code[int(line)-1]:
                # Only add macro if line ends with ";" and line is not a return statement
                # does not make sense to add it after '}'
                # macro added after a return statement will never if registered
                if "_" in var:
                    # Variable name with "_" does not work well with the macros
                    # will cause error when Frama-C runs: "...Cannot resolve variable..."
                    continue
                src_code[int(line)-1] = src_code[int(line)-1]+"Frama_C_show_each_"+var+"("+var+");"

    # Write to disk
    with open(filepath, "w") as f:
        f.write("\n".join(src_code))


def extract_vsa_discrete(value_set_str):
    """
    return location,variable,value set
    """
    # Match with [] for range and {} for discrete
    sep = ";"
    get_values = lambda values: [int(v) for v in values]

    try:
        splitted = value_set_str.split(sep)
        # Get value set
        values = get_values(splitted)
    except:
        return []  # Could be [--..--] instead of an actual range
    return values    


def extract_vsa_range(value_set_str, value_set_limit):
    """
    return location,variable,value set
    """
    # Match with [] for range and {} for discrete
    sep = ".."
    get_values = lambda values: list(range(int(values[0]), int(values[1])+1))

    try:
        splitted = value_set_str.split(sep)
        if int(splitted[1]) - int(splitted[0]) > value_set_limit:
            # Value range too large, MemoryError later
            # Prematurely terminate
            return []
        # Get value set
        values = get_values(splitted)
    except:
        return []  # Could be [--..--] instead of an actual range
    return values    


