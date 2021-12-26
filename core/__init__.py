import json
import os

from time import perf_counter

from collections import defaultdict, namedtuple

from .utilities import (get_configs, framac_output_split, get_file_content,
                       shell_exec, parse_args)


class Zfp:
    """Class to construct zero footprint opaque predicates in src code."""

    PARAMS_STRUCT = namedtuple('PARAMS_STRUCT',
                               ('obfuscation framac_vars ignored_files '
                                'ignored_functions value_set_limit'))

    def __init__(self, wdir, configs):
        """Init variables and perform obfuscation.

        Args:
            wdir: working directory

        Return:
            None
        """
        self.wdir = wdir  # working directory in /tmp folder
        self.ignored_lines = defaultdict(list)
        # Useful statistic
        self.failed_vsa2op = []  # numbers of unsat
        self.failed_vsa = []  # too simple. A value set of just 0
        self.framac_runtime = 0
        self.line_nums = 0
        self.op_nums = 0

        self.params = Zfp.PARAMS_STRUCT(configs['obfuscation'],
                                    configs['framac_vars'],
                                    configs['ignored_files'],
                                    configs['ignored_functions'],
                                    configs['value_set_limit'])

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
        """Filepath to the value analysis output.

        Returns:
            filepath to store the vsa.json file
        """
        return os.path.join(self.wdir, 'vsa.json')

    def _iterate_c_files(self, method, args=()):
        """Call `method` on each C file found.

        Args:
            method: function to call each c file on
            args: arguments to pass to method

        Return:
            None
        """
        for root, _, files in os.walk(self.wdir):
            for filename in files:
                if not filename.endswith('.c'):
                    continue
                if filename in self.params.ignored_files:
                    continue
                # Get paht to each c source file
                filepath = os.path.join(root, filename)
                # Call method
                method(filepath, *args)

    def _remove_comments(self, filepath):
        """Comments might mess with later pipeline for identifying oneliner.

        Args:
            filepath: file to remove comments from

        Return:
            None
        """
        cmd = 'gcc -fpreprocessed -dD -E -P ' + filepath
        cmtless_src = shell_exec(cmd)

        with open(filepath, 'w') as f:
            f.write(cmtless_src)

    def _identify_oneliner(self, filepath):
        """Identify oneliner since they are problematic for our pipeline.

        Args:
            filepath: file to identify oneliner code in

        Return:
            None
        """
        oneliner_begins = ['for ', 'while ', 'if ', 'else if ', 'else ']

        src_code = get_file_content(filepath, return_type='list')
        for i, line in enumerate(src_code):
            oneliner_test = [line.find(o) for o in oneliner_begins]
            # get index to first character of the oneliner
            oneliner_index = next(
                (i for i, x in enumerate(oneliner_test) if x != -1),
                None,
            )
            if oneliner_index is None:
                continue

            # beginning of one-liner detected
            # identify opening brace "{"
            # If keywords such as else, for, if, else, else if, while, "}"
            # is detected before the opening brace, then it is a one-liner
            potential_oneliner_start = line[oneliner_index:]

            # last line of source code
            if i == len(src_code)-1:
                if '{' not in potential_oneliner_start:
                    basename = os.path.basename(filepath)
                    self.ignored_lines[basename].append(i+1)
                break

            # not last line of source code
            lines_of_interest = src_code[i:]
            # start search from where oneliner begins
            lines_of_interest[0] = potential_oneliner_start

            oneliner_loc = 0
            for ii, l in enumerate(lines_of_interest):
                # iterate if a keyword and "{" is not found
                openbrace_test = l.find('{')
                oneliner_find = l.find(';')
                if oneliner_find != -1:
                    # first statement since oneliner start
                    # +1 to account for counting from 0
                    oneliner_loc = i+ii+1

                # filter keywords_test of -1 since that is when find() fails
                keywords = filter(
                        lambda x: x != -1,
                        [l.find(o) for o in oneliner_begins+['}']],
                )

                if not keywords and openbrace_test != -1:
                    # empty list
                    # no keyword found
                    # not a oneliner!
                    break
                else:
                    if openbrace_test == -1:
                        # found a keyword before "{". A oneliner
                        (self.ignored_lines[os.path.basename(filepath)]
                         .append(oneliner_loc))
                        break
                    # a keyword and "{" are both found on current line
                    # not a oneliner! EX: } else {
                    break

    def _perform_injection(self):
        """Insert synthesized opaque predicates back to source."""
        for filepath in self.opaque_predicates.keys():
            # Each `filepath` is a relative path to a C source file
            src_code = get_file_content(os.path.join(self.wdir, filepath),
                                        return_type='list')
            for line_number, ops in self.opaque_predicates[filepath].items():
                if not src_code[int(line_number)-1].isspace():
                    # make sure to insert at end of an instruction 
                    # signify by ';', '}', '{'
                    if src_code[int(line_number)-1].rstrip()[-1] not in  \
                            (';', '}', '{'):
                        continue

                for op in ops:
                    self.op_nums += 1
                    src_code[int(line_number)-1] += op
            with open(os.path.join(self.wdir, filepath), 'w') as f:
                # Write back the obfuscated C source file
                f.write('\n'.join(src_code))

    def _get_opaque_expressions(self):
        """Perform synthesis to get the opaque expressions (construction).

        Returns:
            opaque expressions (ex: y > 10)
        """
        # Run Rosette
        cmd = 'tools/rosette/perform_synthesis.sh '+self.vsa_json
        opaque_expressions = shell_exec(cmd)
        return opaque_expressions

    def _get_opaque_predicates(self):
        """Create opaque predicates (construction+obfuscation).

        Returns:
            fully constructed opaque predicates
        """
        # Format synthesized outputs to prime them for injection
        opaque_predicates = {}
        opaque_expressions = self.opaque_expressions.split('\n')
        index = 0
        for expression in opaque_expressions:
            # t/f <expr>
            # <expr> = <relpath>:<line>:<var> <comparator> <constant>
            label = 'label'+str(index)
            try:
                opaqueness, key, comparator, constant = expression.split(' ')
                filepath, loc, var = key.split(':')
            except:  # noqa
                # Possible faulty expression
                # or value sets that didn't make it as opaque predicates (unsat)
                # EX: f /tmp/x.c:1722:param{.curve_param; .null_param} != 0
                self.failed_vsa2op.append(expression)
                continue

            if filepath not in opaque_predicates:
                opaque_predicates[filepath] = defaultdict(list)

            content = opaque_predicates[filepath]

            if opaqueness == 't':
                content[loc].append(('if('+var+' '+comparator+' '+constant
                                    + '){goto '+label+';}'
                                    + self.params.obfuscation.format(index)
                                    + label+':'))
            elif opaqueness == 'f':
                content[loc].append(('if('+var+' '+comparator+' '+constant+'){'
                                    + self.params.obfuscation.format(index)+'}'))
            index += 1

        return opaque_predicates

    def _get_value_sets(self):
        """Parse, beautify, and save Frama-C's value analysis result as JSON.

        Returns:
            value sets from Frama-C
        """
        value_sets = framac_output_split(self._run_framac(),
                                         self.ignored_lines,
                                         self.params)

        # Save value_sets result (dictionary) as json
        # object of type set is not JSON serializable
        # the JSON file is for Rosette
        value_sets = {k: list(v) for k, v in value_sets.items()}
        with open(self.vsa_json, 'w') as f:
            json.dump(value_sets, f)
        return value_sets

    def _run_framac(self):
        """Perform Value Analysis with Frama-C.

        Returns:
            stdout from Frama-C (in str)
        """
        # call Frama-C (i.e., content of GNUmakefile)
        cmd = 'make -C '+self.wdir
        time_before = perf_counter()
        framac_raw_output = shell_exec(cmd)
        time_after = perf_counter()
        self.framac_runtime = time_after-time_before
        return framac_raw_output
