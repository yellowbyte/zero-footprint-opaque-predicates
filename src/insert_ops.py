import os
import re
import gc
import sys 
import pdb
import stat
import time
import json
import pprint
import shutil
import filecmp
import logging 
import traceback

from random import seed
from random import random
from time import perf_counter 
from datetime import timedelta
from collections import defaultdict, namedtuple

from utilities import *


### Logging
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)


class ZFP:
    """
    Class to construct zero footprint opaque predicates in src code
    """
    PARAMS_STRUCT = namedtuple("PARAMS_STRUCT", "obfuscation framac_vars ignored_files ignored_functions value_set_limit")
    PARAMS = PARAMS_STRUCT(configs["obfuscation"],
                           configs["framac_vars"],
                           configs["ignored_files"], 
                           configs["ignored_functions"], 
                           configs["value_set_limit"])

    def __init__(self, wdir, main_id, clang_id):
        self.wdir = wdir  # working directory in /tmp folder
        self.main_exec = "docker exec -it "+main_id+" "
        self.clang_exec = "docker exec -it "+clang_id+" "
        self.funcs_info = dict()
        # Useful statistic
        self.failed_vsa2op = list()  # numbers of unsat 
        self.failed_vsa = list()  # too simple. A value set of just 0
        self.framac_runtime = 0
        self.line_nums = 0 
        self.op_nums = 0

        # ~~~ main operations ~~~
        # (1) Perform Value Analysis 
        # Run Frama-C to perform value analysis
        # Parse Frama-C's output to identify value-set
        self.value_sets = self._get_value_sets()

        # (2) Perform Synthesis
        # Pass value set to Rosette to perform synthesis
        self.opaque_expressions = self._get_opaque_expressions()
        # Create opaque predicates from synthesis result (i.e., create the if statement)
        self.opaque_predicates = self._get_opaque_predicates()

        # (3) Perform Injection
        # Perform opaque predicates injection
        self._perform_injection()
        # ~~~ main operations ~~~

    @property
    def filepath_json(self):
        """
        Filepath to the value analysis output        
        """
        return os.path.join(self.wdir, "vsa.json")

    def _iterate_c_files(self, method, args=()):
        """
        Call `method` on each C file found
        """
        for root, subdirs, files in os.walk(self.wdir):
            for filename in files:
                if not filename.endswith(".c"):
                    continue
                if filename in ZFP.PARAMS.ignored_files:
                    continue
                # Obfuscate each c source file
                filepath = os.path.join(root, filename)
                # Call method
                method(filepath, *args)

    def _macros_setup(self, filepath):
        """
        Everything up to inserting Frama-C macros
        """
        # remove comment 
        # process hash define 
        # -P: do not insert metadata comment indicating original src lines
        # -fpreprocessed: indicates that the translation unit was already preprocessed and only removes comments. 
        shell2file(filepath, "gcc -fpreprocessed -dD -E -P "+filepath)
        # Our previous gcc preprocess command to remove comment insert metadata on original src lines 
        # This makes clang output bitcode that respect original src lines
        src_code = get_file_content(filepath, return_type="list")
        # Compile each source code file with clang to get bitcode
        self._run_clang(filepath)  # compile src code file to bitcode file
        # Run llvm pass to identify locations of variables and functions
        # NOTE: LLVM pass preprocess .c includes (ex: #include<x.c>). However, src_code will contain code without the 
        #       preprocessed code.
        variables, funcs_end = self._run_llvm(filepath, src_code)
        for func, line_info in funcs_end.items():
            starting_line, ending_line = line_info
            # Information on where the func ends (line) 
            # and the file that it belongs to (filepath)
            self.funcs_info[func] = (starting_line, ending_line, filepath, "\n".join(src_code[int(starting_line)-1:int(ending_line)]))
        # Insert Frama-C macros in variables' locations identified by LLVM Pass
        insert_framac_macros(filepath, src_code, variables)

    def _perform_injection(self):
        """
        Insert synthesized opaque predicates (construction+obfuscation) back to source
        """
        for filepath in self.opaque_predicates.keys():
            src_code = get_file_content(filepath, return_type="list")            
            for line_number, ops in self.opaque_predicates[filepath].items():
                for op in ops:
                    self.op_nums += 1
                    src_code[int(line_number)-1] += op
            with open(filepath, "w") as f:
                f.write("\n".join(src_code))
      
    def _get_opaque_expressions(self):
        """
        Perform synthesis to get the opaque expressions (construction)
        """
        # Run Rosette
        cmd = "/synthesis/get_synthesis.sh "+self.filepath_json
        opaque_expressions = shell_exec(self.main_exec+cmd).rstrip("\r").split("\r\n")
        return opaque_expressions

    def _get_opaque_predicates(self):
        """
        Create opaque predicates (construction+obfuscation) from the opaque expressions (construction)
        """
        # Format Rosette result to prime it for injection
        opaque_predicates = dict()
        index = 0
        for expression in self.opaque_expressions:
            label = "label"+str(index)
            try: 
                opaqueness, key, comparator, constant = expression.split(" ")
                filepath, loc, var = key.split(":")
            except:
                # Possible faulty expression
                # or value sets that didn't make it as opaque predicates (unsat)
                # EX: f /tmp/zfp-0.4780132641092799/src/x509-parser.c:1722:param{.curve_param; .null_param} != 0
                #logging.debug("[_get_opaque_predicates] expression not in correct form: "+expression)
                self.failed_vsa2op.append(expression)
                continue

            if filepath not in opaque_predicates:
                opaque_predicates[filepath] = defaultdict(list)

            content = opaque_predicates[filepath]
            
            if opaqueness == "t":
                content[loc].append("if("+var+" "+comparator+" "+constant+"){goto "+label+";}"+ZFP.PARAMS.obfuscation.format(index)+label+":")
            elif opaqueness == "f":
                content[loc].append("if("+var+" "+comparator+" "+constant+"){"+ZFP.PARAMS.obfuscation.format(index)+"}")
            index += 1

        return opaque_predicates

    def _macro_raw_iterator(self, macro_raw):
        """
        Get Frama-C value analysis result from the inserted macros
        """
        for l in macro_raw:
            # First level filter
            if any([v in l for v in ZFP.PARAMS.framac_vars]):
                # Ignores Frama-C specific variables. They do not exist in original source
                continue
            if any([l.lstrip().startswith(func_name+"_") for func_name in self.funcs_info.keys()]):
                # Frama-C is a bit weird in that it will identify value set for a subroutine's local variables
                # in the subroutine's parent function. Value set identified this way have their variable name
                # starts with the subroutine's name and we ignore them since the variable is out of scope
                continue
            yield l

    def _func_raw_iterator(self, func_raw):
        """
        Get Frama-C value analysis' default result
        """
        func_start = "Values at end of function "
        for l in func_raw:
            struct_name = str()
            # Each line is on a function
            if not l.startswith(func_start):
                continue    
            cur_func = l[len(func_start):l.index(":")]
            if cur_func in ZFP.PARAMS.ignored_functions:
                continue
            if cur_func not in self.funcs_info.keys():
                continue
            yield l

    def _get_value_sets(self):
        """
        Parse, beautify, and save Frama-C's value analysis result as JSON
        """
        # TODO
        func_raw, macro_raw = framac_output_split(self._run_framac())
        value_sets = defaultdict(set)

        # Get value set for macros result (into in-memory data structure)
        blacklist = list()  # vairable whose value set we no longer want
        for l in self._macro_raw_iterator(macro_raw):
            # macro_info = filepath, loc, var_name, potential_value_set_info
            macro_info = get_macro_info(self.wdir, l)
            if not macro_info:
                continue
            get_macro_value_sets(value_sets, macro_info, blacklist, ZFP.PARAMS)

        # Get value set for end of function result (into in-memory data structure)
        func_start = "Values at end of function "
        for l in self._func_raw_iterator(func_raw):
            cur_func = l[len(func_start):l.index(":")]
            func_vars = l[l.index(":"):].split("\n")
            get_func_value_sets(value_sets, cur_func, func_vars, self.funcs_info, ZFP.PARAMS)

        # Save value_sets result (dictionary) as json
        # object of type set is not JSON serializable 
        # value_sets contains loc where loc is function name or where loc is line number
        # the JSON file is for Rosette
        vsa_serializable = dict()
        value_sets_no_empty = {k:v for k,v in value_sets.items() if v}
        for key, val in value_sets_no_empty.items():
            # avoid value set of just 0 since Frama-C will identify a pointer as containing only 0
            # and the way I identify variable for Frama-C macro does not recognize pointer variable
            # ++ 
            # Frama-C will mis-identify complex struct as int. In those cases, the identified value is just a 0
            if len(list(val))==1 and list(val)[0] == 0:
               self.failed_vsa.append(str(key)+":"+str(val))
               continue
            vsa_serializable[key] = list(val)  # val is set
        with open(self.filepath_json, "w") as f:
            json.dump(vsa_serializable, f)
        # The returned value_sets is not used anywhere else 
        # but we exposed it to users for debugging purpose
        return value_sets_no_empty 

    def _run_framac(self):
        """
        Perform Value Analysis with Frama-C
        """
        # TODO
        cmd = "make -C "+self.wdir  # call Frama-C (i.e., make GNUmakefile)
        time_before = perf_counter()
        framac_raw_output = shell_exec(self.main_exec+cmd)
        time_after = perf_counter()
        self.framac_runtime = time_after-time_before
        return framac_raw_output

    def _run_clang(self, filepath):
        """
        Get LLVM bitcode
        """
        filepath_bc = get_filepath_ext(filepath, "bc")
        # cmd: clang -O0 -g -emit-llvm [name].c -c -o [name].bc 
        cmd = "clang -O0 -g -emit-llvm "+filepath+" -c -o "+filepath_bc
        shell_exec(self.clang_exec+cmd)

    def _run_llvm(self, filepath, src_code):
        """
        Run the two LLVM passes
        """
        filepath_bc = get_filepath_ext(filepath, "bc")
        logging.debug("run_llvm: "+filepath)
        logging.debug("run_llvm: "+filepath_bc)
        # Assume in container so directory is: /llvm-base/build
        # cmd: opt -load lib/LLVMFindVars.so -findvars [name].bc
        # layout: line number, variable name, func name
        cmd = "opt -load lib/LLVMFindVars.so -findvars "+filepath_bc
        llvm_vars_output = shell_exec(self.main_exec+cmd)
        # layout: func name, ending line, starting line
        cmd = "opt -load lib/LLVMFuncsEnd.so -funcsend "+filepath_bc
        llvm_funcs_output = shell_exec(self.main_exec+cmd)

        variables = extract_findvars(llvm_vars_output)
        funcs_possible_end = extract_funcsend(llvm_funcs_output)
        return filter_nonexistent_vars(src_code, variables), get_funcs_end(src_code, funcs_possible_end)


def main(wdir, host_src_dir, main_id, clang_id):
    """
    Main
    """
    try: 
        timer_start = perf_counter()
        obfuscated = ZFP(wdir, main_id, clang_id)    
        timer_stop = perf_counter()
    except:
        # Stop Docker
        # If not run this, permission error with rmtree
        shell_exec("docker exec -it "+main_id+" make clean -C "+wdir)  
        shell_exec("docker rm -f "+main_id)
        shell_exec("docker rm -f "+clang_id)
        # Remove tmp working dir
        if configs["delete_metadata"]:
            shutil.rmtree(wdir)
        sys.exit(str(traceback.format_exc()))

    # Compile the obfuscated source code
    shell_exec("docker exec -it "+clang_id+" make -C "+wdir+" -f Makefile")
    new_files = [f for f in filecmp.dircmp(host_src_dir, wdir).right_only 
              if not f.endswith(".json") and not f.endswith(".bc") and not \
              f.endswith(".c") and not f.endswith(".eva") and not f.endswith(".parse")]

    # Move the compiled binary to original directory
    for f in new_files:
        shutil.move(os.path.join(wdir, f), os.path.join(host_src_dir, f))

    # Statistics
    logging.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    logging.info("current: "+host_src_dir)
    logging.info("number of value sets identified: "+str(len(obfuscated.value_sets.keys())))
    logging.info("number of opaque predicates: "+str(obfuscated.op_nums))
    logging.info("time it takes to obfuscate (seconds): "+str(timer_stop-timer_start))
    logging.info("time it takes to obfuscate (formatted): "+str(timedelta(seconds=(timer_stop-timer_start))))
    logging.info("Frama-C runtime (seconds): "+str(obfuscated.framac_runtime))
    logging.info("Frama-C runtime (formatted): "+str(timedelta(seconds=(obfuscated.framac_runtime))))
    logging.info("value sets that didn't make it as opaque predicates, or unsat("+str(len(obfuscated.failed_vsa2op))+")")
    logging.info("value sets that didn't make it as value sets since it's only zero("+str(len(obfuscated.failed_vsa))+")")
    logging.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    logging.info("values that are unsat: ")
    for failed in obfuscated.failed_vsa2op:
        logging.info(pprint.pformat(failed, indent=4))
    logging.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    logging.info("values that are too simple: ")
    for failed in obfuscated.failed_vsa:
        logging.info(pprint.pformat(failed, indent=4))


if __name__ == "__main__":
    # Set configurations
    host_src_dir = sys.argv[1]
    set_configs(host_src_dir)

    # Create tmp working dir
    millis = int(round(time.time() * 1000))
    seed(millis)  # Make random() as random as possible
    wdir = os.path.join(configs["metadata_dir"], "zfp-"+str(random()))
    shutil.copytree(host_src_dir, wdir)

    # Set up log handlers
    fh = logging.FileHandler(os.path.join(host_src_dir, "zfp.log"))
    fh.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    logger.addHandler(sh)

    # Start Docker
    shell_exec("docker run -t -d -v "+wdir+":"+wdir+" --name zfp-main zfp-main")
    shell_exec("docker run -t -d -v "+wdir+":"+wdir+" --name zfp-clang zfp-clang")
                
    # Get Docker containers' info
    main_id = shell_exec("docker ps -qf name=^zfp-main$")
    clang_id = shell_exec("docker ps -qf name=^zfp-clang$")

    # Main
    main(wdir, host_src_dir, main_id, clang_id)

    # Stop Docker
    # If not run this, permission error with rmtree
    # due to files created by Frama-C
    shell_exec("docker exec -it "+main_id+" make clean -C "+wdir)  
                                                                   
    shell_exec("docker rm -f "+main_id)
    shell_exec("docker rm -f "+clang_id)

    # Remove tmp working dir
    if configs["delete_metadata"]:
        shutil.rmtree(wdir)
