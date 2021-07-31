import os
import sys
import pdb

from pprint import pprint
from binaryninja import *


COMPARE = {
    "MLIL_CMP_E":" == ",
    "MLIL_CMP_NE":" != ",
    "MLIL_CMP_SLT":" < ",
    "MLIL_CMP_ULT":" < ",
    "MLIL_CMP_SLE":" <= ",
    "MLIL_CMP_ULE":" <= ",
    "MLIL_CMP_SGE":" >= ",
    "MLIL_CMP_UGE":" >= ",
    "MLIL_CMP_SGT":" > ",
    "MLIL_CMP_UGT":" > "
}

def eval_all_same(value_set, cond):
    result = eval('['+cond+' for x in value_set]')
    return result

def unsigned2signed(num):
    if(num & 0x80000000):
        num = -0x100000000 + num
    return num

def main(filepath, op_locations, outfile):
    """
    """
    bv = BinaryViewType.get_view_of_file(filepath)
    if bv is None:
        print("Couldn't open {}".format(filepath))
        sys.exit()

    op_bbs = list()
    # NOTE: op_locations not used. For debugging 
    op_locations = [int(o.rstrip("\n").rstrip("L"),16) for o in op_locations]
#    pprint([hex(a) for a in op_locations])
    for func in bv.functions:
        for bb in func.mlil.ssa_form:
            # bb ends with OP
            if_cond = bb[-1]  # the if condition (opaque predicate) instruction. 
                              # Always the last instruction of the bb
            addr = hex(bb.get_disassembly_text()[-1].address)
            
            if not hasattr(if_cond, 'condition'):
                # already seen. MLIL SSA splits instruction into multiple instructions
                # so the if statment can be split into multiple instructions
                continue 
            # const value 
            if if_cond.condition.possible_values.type == RegisterValueType.ConstantValue:
                # just const value
                # detection successful in this case since value set is of size 1
                outfile.write(addr+'\n')    
                continue

            # compare register or memory with a constant
            # in MLIL, stack variable is now a variable
            if len(if_cond.vars_read) == 1 and not hasattr(if_cond.condition, 'left'):
                # cond variable
                actual_cond = func.mlil.ssa_form.get_ssa_var_definition(if_cond.vars_read[0]).src
            else:
                actual_cond = if_cond.condition

            if not hasattr(actual_cond, 'left'):
                if not hasattr(actual_cond, 'src'):
                    # an unimplemented instruction
                    continue
                # a cond:# or c:# object. Get definition to retrieve condition
                actual_cond = func.mlil.ssa_form.get_ssa_var_definition(actual_cond.src).src                
            if str(actual_cond.left.possible_values) == '<undetermined>':
                # value cannot be determined
                continue
            if str(actual_cond.right.value) == '<undetermined>':
                # not comparing with a constant
                continue
            # recreate the opaque predicate as a string
            const = actual_cond.right.value.value
            operation = COMPARE[actual_cond.operation.name]
            op_str = "x"+operation+str(unsigned2signed(const))
            # retrieve the value set
            if hasattr(actual_cond.left.possible_values, 'value'):
                possiblevalueset = {actual_cond.left.possible_values.value}
            elif hasattr(actual_cond.left.possible_values, 'values'):
                possiblevalueset = actual_cond.left.possible_values.values
            else:
                # the following possible values are in ranges 
               tmp = []
               for _range in actual_cond.left.possible_values.ranges:
                   if len(range(_range.start,_range.end+1,_range.step)) >= 100000000:
                        # need a bound or else if value set too large Python will crash (intractable).
                        # the value is the same as the value set bound in our obfuscation pipeline
                        continue
                   for i in range(_range.start,_range.end+1,_range.step):
                       tmp.append(i)
               possiblevalueset = set(tmp)
            # evaluate the value set
            eval_result = eval_all_same(possiblevalueset, op_str)
            if (False in eval_result) and (True in eval_result):
                # not all elements in value set evaluated to the same value
                continue
            else:
                # binja correctly identify 
                outfile.write(hex(bb.get_disassembly_text()[-1].address)+'\n')


if __name__ == "__main__":
    filepath = sys.argv[1]  # give path to the binary
    proj_dir = os.path.dirname(filepath)  # get path to folder containing the binary
    with open(os.path.join(proj_dir, "op_locations.zfp"), "r") as f:
        op_locations = f.readlines()

    # output to binja.zfp the opaque predicates that it can correctly identify
    with open(os.path.join(proj_dir, "vsa", "binja.zfp"), "w") as outfile:
        main(filepath, op_locations, outfile)
