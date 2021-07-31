## Overview

Zero Footprint Opaque Predicates obfuscate single-file C source code with opaque predicates that syntactically and semantically resemble real predicates in order to prevent heuristic attacks (e.g., pattern matching) while maintaining resilience against automated attacks. Opaque predicates have a reputation as a low-hanging fruit because it is easy to deobfuscate once detected (unlike VM obfuscation). However, opaque predicates can be very powerful when undetected because their obfuscation have the flexiblity to be not just any instruction sequence (i.e., code bloat) but also junk bytes that can further cause anti-disassembly (i.e., disassembly desynchronization).

Our inserted opaque predicates' obfuscation is a deterministic and impossible instruction sequence. This is to allow us to detect our opaque predicates so we can evaluate them with deobfuscation tools. In practice, the obfuscation should not always be the same sequence (or else it is easily detected from the obfuscation). 

_Current tool implementation has some pitfalls (check <b>Other Notes and Pitfalls</b> section). To avoid those pitfalls, the next step is to implement most of the obfuscation pipeline as a Frama-C plugin; this will also help make the tool more user-friendly. A list of our TODOs can be found in todos.md_

## Getting Started

#### Requirements
* Python 3.7 and above
* Docker 

#### Installation (assumed in project root directory)
1. source helpers
2. buildc (will build 2 docker images. Note that they will take up 7.75GB)

#### To Run (assumed in project root directory)
* python3.7 src/insert\_ops.py [filepath to the folder containing target source code]
  * make sure the folder containing target source code has the following additional files: 
    * `Makefile`: standard Makefile. The code will call `make` to compile the codebase after obfuscation. This is the default behavior but can be changed. 
    * `GNUmakefile`: a Makefile with instructions on how to run Frama-C for the specified codebase. The number of value sets that can be inferred heavily depend on the settings in this file.
  * Check debugging\_tips.md if the program runs into errors.

#### Settings
The following are settings user can change:
* `metadata_dir`: path to directory where metadata will be stored. Default to /tmp
* `delete_metadata`: set to either True or False. Decides whether to delete the metadata folder. Default to True
* `obfuscation`: what non-executable code to inject as the obfuscation
* `value_set_limit`: the max value set length to consider. Too small may lead to few synthesized opaque predicates. Too large may lead to crash. Default to 100000000

User can specify the settings in a JSON file named "zfp.json" and place that file in the root directory of the folder containing the target source code. An example JSON file can be seen below:
```json
{
    "metadata_dir": "/tmp",
    "delete_metadata": True,
    "obfuscation": "__asm__ __volatile__(\"xor %eax, %eax;xor %esp, %esp;xor %ebp, %ebp; add %eax, %esp;\");",
    "value_set_limit": 100000000
}
```

User can also directly change the settings by updating the `configs` dictionary  at `src/utilities/__init__.py`

## Files 

#### scripts
* `BinValueSetEval.py`: given an obfuscated binary, check if binary abstract interpretation (available in BinaryNinja) can identify our opaque predicates by evaluating variable's value set under the corresponding predicate
* `identify_zfp.py`: print all the opaque predicates locations
  * We purposely make our opaque predicates' obfuscation (i.e., injected non-executable code) deterministic so we can detect them for evaluation with other deobfuscation tools
* `perform_eval.py`: given a file containing the correct opaque predicates locations (can be retrieved with identify\_zfp.py) and another file containing the opaque predicates locations identified by a deobfuscation tool, evaluate how well the deobfuscation tool performs
* `run_all`: a host of bash functions to help perform evaluations/obfuscations on multiple binaries
  * run this command to use: source scripts/run\_all

## Other Notes and Pitfalls

* Due to dependency issues, we decide to split tools across two different docker containers. The newest version of Frama-C when we started (21.1) requires opam version >= 2 and opam version >= 2 is only available on Ubuntu 18 and above. However, we ran into problem when we needed clang 3.8 and clang 3.8 is not available on Ubuntu 18 and above. The reason we needed clang 3.8 is because our LLVM pass (LLVM pass are used to identify the locations to insert Frama-C macros) is written for LLVM 3.8. The central code that provides the coordination in our obfuscation pipeline is the file insert\_ops.py; it will spun up the necessary container to perform the obfuscation and also perform the necessary cleanup afterward. For more thoughts on this, check todos.md.
* Cannot obfuscate code that contains recursive calls. This is a limitation of one of our dependencies, Frama-C
  * stated in [Frama-C's website under the "Technical Notes" section](https://www.frama-c.com/fc-plugins/eva.html).
* NOTE: the following restrictions are due to our approach of parsing Frama-C's output. A custom Frama-C plugin will avoid them (check todos.md).
  * Target C file cannot condense if statement or for loop to one line. This is because the value set identified by Frama-C will be for the code inside that one line if statement or for loop, but the corresponding synthesized opaque predicate will be outside of the one line if statement or for loop when inserted into the source code.
  * Target C file should avoid using unsigned variables. Our tool might synthesize an opaque predicate that compares an unsigned variable to -1 but common compiler (e.g., clang, gcc) will still use unsigned machine comparison (e.g., JAE) instead of signed machine comparison (e.g., JGE) since the variable type is unsigned. If this is the case, then the obfuscation or non-executable code can be executed.
  * In the target C file, any variable used in a for loop init needs to be declared outside the for loop. Since if Frama-C identifies the init variable as containing a value set at the end of a function, our tool might synthesize an opaque predicate for that init variable but that init variable is out-of-scope at end of function if not declared outside the for loop.
