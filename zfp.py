#!/usr/bin/env python3

"""
This is the entry point for the ZFP obfuscation tool.
"""

import logging
import os
import shutil
import sys
import time
from datetime import timedelta
from random import random, seed
from time import perf_counter

from core import Zfp
from core import parse_args, shell_exec, get_configs


# Logging
logger = logging.getLogger('')
logger.setLevel(logging.DEBUG)


def main(wdir, sdir, configs):
    """Perform Main.

    Args:
        wdir: working directory
        sdir: orginal directory that contains the code to obfuscate

    Return:
        None
    """
    timer_start = perf_counter()
    obfuscated = Zfp(wdir, configs)
    timer_stop = perf_counter()

    # Compile the obfuscated source code
    shell_exec(' make -C '+wdir+' -f Makefile')

    # Statistics
    logging.info('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
    logging.info('current: '
                 + sdir)
    logging.info('number of value sets identified: '
                 + str(len(obfuscated.value_sets.keys())))
    logging.info('number of opaque predicates: '
                 + str(obfuscated.op_nums))
    logging.info('time it takes to obfuscate (seconds): '
                 + str(timer_stop-timer_start))
    logging.info('time it takes to obfuscate (formatted): '
                 + str(timedelta(seconds=(timer_stop-timer_start))))
    logging.info('Frama-C runtime (seconds): '
                 + str(obfuscated.framac_runtime))
    logging.info('Frama-C runtime (formatted): '
                 + str(timedelta(seconds=(obfuscated.framac_runtime))))

    # Move the compiled binary to original directory
    # Copy back everything except C files, zfp.log and vsa.json.
    # C files are modified by this tool (with OP added in)
    # zfp.log in wdir is the old log
    for subdir, _, files in os.walk(wdir):
        for _file in files:
            if _file.endswith('.c'):
                continue
            if _file == 'vsa.json':
                continue
            if _file == 'zfp.log':
                continue
            # analysis results from Frama-C. Don't need
            # or else can't rerun unless user manually delete these folders
            if subdir.endswith('.eva'):
                continue
            if subdir.endswith('.parse'):
                continue

            relative_filepath = os.path.relpath(subdir, wdir)
            shutil.move(os.path.join(wdir, relative_filepath, _file),
                        os.path.join(sdir, relative_filepath, _file))

    # Remove tmp working dir
    if configs['delete_metadata']:
        shutil.rmtree(wdir)


if __name__ == '__main__':
    # Commandline argument parsing
    parse_args()

    # Create tmp working dir (wdir)
    # wdir: working directory (containing metadata like obfuscated source, etc.)
    # sdir: source directory (containing source code to obfuscate)
    configs = get_configs()
    sdir = configs['srcfolder']
    millis = int(round(time.time() * 1000))
    seed(millis)  # Make random() as random as possible
    wdir = os.path.join(configs['metadata_dir'],
                        'zfp-'+str(random()))  # noqa:S311
    shutil.copytree(sdir, wdir)

    # Set up logging
    fh = logging.FileHandler(os.path.join(sdir, 'zfp.log'), mode='w')
    fh.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    logger.addHandler(sh)

    # Main
    main(wdir, sdir, configs)
