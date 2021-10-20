from .framac_engineer import *

import os 
import pdb
import json
import logging 
import subprocess

from pathlib import Path


### Configurations ###
######################
configs = {
    "metadata_dir": "/tmp",

    "delete_metadata": True,

    ### Obfuscation for the inserted opaque predicates 
    # We purposely make it deterministic so we can detect our opaque predicates for evaluation with other deobfuscation tools.
    # Also in practice, the obfuscation shouldn't always be the same sequence. Or else it can be easily detected from the obfuscation.
    "obfuscation": "__asm__ __volatile__(\"xor %eax, %eax;xor %esp, %esp;xor %ebp, %ebp; add %eax, %esp;\");",

    # NOTE: python can only hold so many values in-memory. Higher "value_set_limit" allows you to possibly generate
    #       more opaque predicates but will also slow down program or worst-case, prematurely terminate it.
    "value_set_limit": 100000000,  # we found this value to work well for our benchmark. Can choose a larger value if desired.
    #"value_set_limit": 10000,    # However, if program terminates prematurely, choose a smaller value (like this one)

    ### Specific to running Frama-C
    "framac_macro": "Frama_C_show_each_",
    "framac_vars": ["__retres", "Frama_C_entropy_source", 
                    "__fc_", "__realloc_", "__malloc_"],
    # stubs to analyze frama-c
    "ignored_files": ["fc_stubs.c", "fc_stubs.h"],
    # function specific to the frama-c value analysis
    "ignored_functions": ["eva_main"],
}


def shell_exec(cmd):
    """
    Run `cmd` in shell
    """
    logging.debug(cmd)
    # Capture_output argument is only available in Python >= 3.7
    result = subprocess.run(cmd.split(), capture_output=True)
    logging.debug("SHELL_EXEC: "+result.stdout.decode("utf-8").rstrip("\n"))
    return result.stdout.decode("utf-8").rstrip("\n")


def get_file_content(filepath, return_type="list"):
    """
    Bring content of file at `filepath` to memory
    """
    filtered = list()
    with open(filepath, "r") as f:
        if return_type == "list":
            content = [l.rstrip("\n") for l in f.readlines()]
        else:
            content = f.read()
    return content
