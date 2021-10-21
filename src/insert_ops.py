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
import argparse
import traceback

from time import perf_counter 
from datetime import timedelta
from random import random, seed
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

    def __init__(self, wdir):
        self.wdir = wdir  # working directory in /tmp folder
        self.funcs_info = dict()
        self.ignored_lines = defaultdict(list)
        # Useful statistic
        self.failed_vsa2op = list()  # numbers of unsat 
        self.failed_vsa = list()  # too simple. A value set of just 0
        self.framac_runtime = 0
        self.line_nums = 0 
        self.op_nums = 0

        # ~~~ main operations ~~~
        # (0) Pre-Process or Remove Comments
        self._iterate_c_files(self._remove_comments)

        # (1) One-Liner Identification
        self._iterate_c_files(self._identify_oneliner)

        # (2) Perform Value Analysis 
        # Run Frama-C to perform value analysis
        # Parse Frama-C's output to identify value set
        self.value_sets = self._get_value_sets()

        # (3) Perform Synthesis
        # Pass value set to Rosette to perform synthesis
        self.opaque_expressions = self._get_opaque_expressions()
        # Create opaque predicates from synthesized output
        self.opaque_predicates = self._get_opaque_predicates()

        # (4) Perform Injection
        # Perform opaque predicates injection
        self._perform_injection()
        # ~~~ main operations ~~~

    @property
    def vsa_json(self):
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
                # Get paht to each c source file
                filepath = os.path.join(root, filename)
                # Call method
                method(filepath, *args)

    def _remove_comments(self, filepath):
        """
        Comments might mess with later pipeline for identifying oneliner
        """
        cmd = "gcc -fpreprocessed -dD -E -P " + filepath
        cmtless_src = shell_exec(cmd) 

        with open(filepath, "w") as f: 
            f.write(cmtless_src)

    def _identify_oneliner(self, filepath):
        """
        Identify oneliner since they are problematic for our pipeline
        """
        oneliner_begins = ["for ", "while ", "if ", "else if ", "else "]

        src_code = get_file_content(filepath, return_type="list")        
        for i, line in enumerate(src_code):
            oneliner_test = [line.find(o) for o in oneliner_begins]
            # get index to first character of the oneliner
            oneliner_index = next((i for i, x in enumerate(oneliner_test) if x!=-1), None)
            if oneliner_index is not None:
                # beginning of one-liner detected
                
                # identify opening brace "{"
                # If keywords such as else, for, if, else, else if, while, "}" 
                # is detected before the opening brace, then it is a one-liner

                potential_oneliner_start = line[oneliner_index:]
                
                # last line of source code
                if i == len(src_code)-1:  
                    if "{" not in potential_oneliner_start:
                        self.ignored_lines[os.path.basename(filepath)].append(i+1)
                    break

                # not last line of source code
                lines_of_interest = src_code[i:] 
                lines_of_interest[0] = potential_oneliner_start  # start search from where
                                                                 # oneliner begins
                oneliner_loc = 0
                for ii,l in enumerate(lines_of_interest):
                    openbrace_test = l.find("{")
                    oneliner_find = l.find(";")
                    if oneliner_find != -1:
                        # first statement since oneliner start
                        oneliner_loc = i+ii+1  # +1 to account for counting from 0

                    # filter keywords_test of -1 since that is when find() fails
                    keywords_test = filter(lambda x:x!=-1, 
                                           [l.find(o) for o in oneliner_begins+["}"]])

                    keywords = list(keywords_test)
                    if keywords == list(): 
                        # no keyword found
                        if openbrace_test != -1:
                            # not a oneliner! 
                            break
                    else: 
                        if openbrace_test == -1:
                            # found a keyword before "{". A oneliner
                            self.ignored_lines[os.path.basename(filepath)].append(oneliner_loc) 
                            break

                        # a keyword and "{" are both found on current line
                        # not a oneliner! EX: } else {
                        break

                    # end of loop reached if a keyword is not found and "{" is not found

    def _perform_injection(self):
        """
        Insert synthesized opaque predicates (construction+obfuscation) back to source
        """
        for filepath in self.opaque_predicates.keys():
            # Each `filepath` is a relative path to a C source file
            src_code = get_file_content(os.path.join(self.wdir, filepath), return_type="list")            
            for line_number, ops in self.opaque_predicates[filepath].items():
                for op in ops:
                    self.op_nums += 1
                    src_code[int(line_number)-1] += op
            with open(os.path.join(self.wdir, filepath), "w") as f:
                # Write back the obfuscated C source file
                f.write("\n".join(src_code))
      
    def _get_opaque_expressions(self):
        """
        Perform synthesis to get the opaque expressions (construction)
        """
        # Run Rosette
        cmd = "/synthesis/perform_synthesis.sh "+self.vsa_json
        opaque_expressions = shell_exec(cmd)
        return opaque_expressions

    def _get_opaque_predicates(self):
        """
        Create opaque predicates (construction+obfuscation) from the opaque expressions (construction)
        """
        # Format synthesized outputs to prime them for injection
        opaque_predicates = dict()
        opaque_expressions = self.opaque_expressions.split("\n")
        index = 0
        for expression in opaque_expressions:
            # t/f <expr>
            # <expr>= <relative filepath>:<line number>:<variable name> <comparator> <constant>
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

    def _get_value_sets(self):
        """
        Parse, beautify, and save Frama-C's value analysis result as JSON
        """
        value_sets = framac_output_split(self._run_framac(), self.ignored_lines, ZFP.PARAMS)

        # Save value_sets result (dictionary) as json
        # object of type set is not JSON serializable 
        # the JSON file is for Rosette
        value_sets = {k:list(v) for k,v in value_sets.items()}
        with open(self.vsa_json, "w") as f:
            json.dump(value_sets, f)
        return value_sets

    def _run_framac(self):
        """
        Perform Value Analysis with Frama-C
        """
        cmd = "make -C "+self.wdir  # call Frama-C (i.e., content of GNUmakefile)
        time_before = perf_counter()
        framac_raw_output = shell_exec(cmd)
        time_after = perf_counter()
        self.framac_runtime = time_after-time_before
        # clean up residue
        framac_raw_output.split("make: Leaving directory", 1)[0]
        return framac_raw_output


def main(wdir, host_src_dir):
    """
    Main
    """
    try: 
        timer_start = perf_counter()
        obfuscated = ZFP(wdir)    
        timer_stop = perf_counter()
    except:
        # Remove tmp working dir
        if configs["delete_metadata"]:
            shutil.rmtree(wdir)
        sys.exit(str(traceback.format_exc()))

    # Compile the obfuscated source code
    shell_exec(" make -C "+wdir+" -f Makefile")
    new_files = [f for f in filecmp.dircmp(host_src_dir, wdir).right_only 
              if not f.endswith(".json") and not f.endswith(".bc") and not \
              f.endswith(".c") and not f.endswith(".eva") and not f.endswith(".parse")]

    # Statistics
    logging.info("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    logging.info("current: "+host_src_dir)
    logging.info("number of value sets identified: "+str(len(obfuscated.value_sets.keys())))
    logging.info("number of opaque predicates: "+str(obfuscated.op_nums))
    logging.info("time it takes to obfuscate (seconds): "+str(timer_stop-timer_start))
    logging.info("time it takes to obfuscate (formatted): "+str(timedelta(seconds=(timer_stop-timer_start))))
    logging.info("Frama-C runtime (seconds): "+str(obfuscated.framac_runtime))
    logging.info("Frama-C runtime (formatted): "+str(timedelta(seconds=(obfuscated.framac_runtime))))

    # Move the compiled binary to original directory
    # Copy back everything except C files, zfp.log and vsa.json. C files are modified by this tool (with OP added in)
    # zfp.log in wdir is the old log
    for subdir, dirs, files in os.walk(wdir):
        for _file in files:
            if _file.endswith(".c"):
                continue
            if _file == "vsa.json":
                continue
            if _file == "zfp.log":
                continue
            # analysis results from Frama-C. Don't need
            # or else can't rerun unless user manually delete these folders
            if subdir.endswith(".eva"):
                continue
            if subdir.endswith(".parse"):
                continue

            relative_filepath = os.path.relpath(subdir, wdir)
            shutil.move(os.path.join(wdir, relative_filepath, _file), os.path.join(host_src_dir, relative_filepath, _file))


if __name__ == "__main__":
    # Set configurations
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--metadatadir", type=str, required=False, help="path to directory where metadata will be stored. Default to /tmp")
    parser.add_argument("-l", "--limits", type=int, required=False, help="the max value set length to consider. Too small may lead to few synthesized opaque predicates. Too large may lead to crash. Default to 100000000")
    parser.add_argument('srcfolder', type=str, help="folder containing source code to obfuscate")
    parser.add_argument("--delmetadata", action=argparse.BooleanOptionalAction, required=False, help="set to either True or False. Decides whether to delete the metadata folder. Default to True")
    args = parser.parse_args()
    set_configs(args)
    host_src_dir = args.srcfolder

    # Create tmp working dir (wdir)
    millis = int(round(time.time() * 1000))
    seed(millis)  # Make random() as random as possible
    wdir = os.path.join(configs["metadata_dir"], "zfp-"+str(random()))
    shutil.copytree(host_src_dir, wdir)

    # Set up logging 
    fh = logging.FileHandler(os.path.join(host_src_dir, "zfp.log"), mode="w")
    fh.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    logger.addHandler(sh)

    # Main
    main(wdir, host_src_dir)

    # Remove tmp working dir
    if configs["delete_metadata"]:
        shutil.rmtree(wdir)
