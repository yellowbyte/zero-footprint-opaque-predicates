"""Contains general utilities functions and global configs."""
import logging
import argparse
import subprocess  # noqa

from .framac_engineer import *  # noqa

# Configurations
######################
__CONFIGS = {
    'metadata_dir': '/tmp',  # noqa

    'delete_metadata': True,

    'srcfolder': None,

    # Obfuscation for the inserted opaque predicates
    # We purposely make it deterministic so we can detect our
    # opaque predicates for evaluation with other deobfuscation tools.
    # Also in practice, the obfuscation shouldn't always be the same sequence.
    # Or else it can be easily detected from the obfuscation.
    'obfuscation': '__asm__ __volatile__(\"xor %eax, %eax;xor %esp, %esp;xor %ebp, %ebp; add %eax, %esp;\");',  # noqa

    # NOTE: python can only hold so many values in-memory.
    #       Higher "value_set_limit" allows you to possibly generate
    #       more opaque predicates but will also slow down program or
    #       worst-case, prematurely terminate it.
    'value_set_limit': 100000000,  # we found this value to work well for our
                                   # benchmark. Can choose a larger value.
    # However, if program terminates prematurely, choose a smaller value (10000)

    # Specific to running Frama-C
    'framac_macro': 'Frama_C_show_each_',
    'framac_vars': ['__retres', 'Frama_C_entropy_source',
                    '__fc_', '__realloc_', '__malloc_'],
    # stubs to analyze frama-c
    'ignored_files': ['fc_stubs.c', 'fc_stubs.h'],
    # function specific to the frama-c value analysis
    'ignored_functions': ['eva_main'],
}


def parse_args():
    """
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-m',
                        '--metadatadir',
                        type=str,
                        required=False,
                        help=('path to directory where metadata will be stored.'
                              'Default to /tmp'))
    parser.add_argument('-l',
                        '--limits',
                        type=int,
                        required=False,
                        help=('the max value set length to consider.'
                              'Too small may lead to few synthesized opaque'
                              'predicates. Too large may lead to crash.'
                              'Default to 100000000'))
    parser.add_argument('srcfolder',
                        type=str,
                        help='folder containing source code to obfuscate')
    parser.add_argument('--delmetadata',
                        action=argparse.BooleanOptionalAction,
                        required=False,
                        help=('set to either True or False. Decides whether to'
                              'delete the metadata folder. Default to True'))
    args = parser.parse_args()
    # Set configurations
    set_configs(args)


def get_configs():
    """
    """
    global __CONFIGS
    return __CONFIGS


def set_configs(args):
    """Set `configs` based on commandline arguments `args`.

    Args:
        args: commandline arguments

    Return:
        None
    """
    global __CONFIGS

    __CONFIGS['srcfolder'] = args.srcfolder

    if args.metadatadir:
        __CONFIGS['metadata_dir'] = args.metadatadir
    if args.delmetadata is False:
        # by default True
        __CONFIGS['delete_metadata'] = False
    if args.limits:
        __CONFIGS['value_set_limit'] = args.limits


def shell_exec(cmd):
    """Run `cmd` in shell.

    Args:
        cmd: command to run by the shell

    Returns:
        output from running cmd in the shell
    """
    logging.debug(cmd)
    # Capture_output argument is only available in Python >= 3.7
    result = subprocess.run(cmd.split(), capture_output=True)  # noqa
    logging.debug('SHELL_EXEC: '+result.stdout.decode('utf-8').rstrip('\n'))
    return result.stdout.decode('utf-8').rstrip('\n')


def get_file_content(filepath, return_type='list'):
    """Bring content of file at `filepath` to memory.

    Args:
        filepath: file to read content of
        return_type: data structure to represent content in
    """
    with open(filepath, 'r') as f:
        if return_type == 'list':
            content = [line.rstrip('\n') for line in f.readlines()]
        else:
            content = f.read()
    return content
