import sys

# given a binary obfuscated with zfp, identify all their virtual addresses
# We purposely makes our opaque predicates' obfuscation (i.e., injected non-executable code) deterministic so we can detect it for evaluation with other deobfuscation tools


from binaryninja import *


def main(filepath):
    """
    """
    bv = BinaryViewType.get_view_of_file(filepath)
    bv.update_analysis_and_wait()
    if bv is None:
        print("Couldn't open {}".format(filepath))
        sys.exit()

    for func in bv.functions:
        for bbl in func.basic_blocks:
            instrs = bbl.get_disassembly_text()
            # Pattern matching our obfuscation
            if not (
                   str(instrs[0].tokens[0]) == "xor" and str(instrs[0].tokens[2]) == "eax" and str(instrs[0].tokens[4]) == "eax" and 
                   str(instrs[1].tokens[0]) == "xor" and str(instrs[1].tokens[2]) == "esp" and str(instrs[1].tokens[4]) == "esp" and
                   str(instrs[2].tokens[0]) == "xor" and str(instrs[2].tokens[2]) == "ebp" and str(instrs[2].tokens[4]) == "ebp" and
                   str(instrs[3].tokens[0]) == "add" and str(instrs[3].tokens[2]) == "esp" and str(instrs[3].tokens[4]) == "eax"
               ):
                continue
            assert len(bbl.incoming_edges) == 1
            parent_bbl = bbl.incoming_edges[0].source
            print(hex(parent_bbl.start + (parent_bbl.length-parent_bbl[-1][-1])))


if __name__ == "__main__":
    main(sys.argv[1])
