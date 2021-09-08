## Overview

[Zero Footprint Opaque Predicates](https://rdcu.be/cpnNf) obfuscate single-file C source code with opaque predicates that syntactically and semantically resemble real predicates in order to prevent heuristic attacks (e.g., pattern matching) while maintaining resilience against automated attacks. Opaque predicates can be very powerful when undetected because their obfuscation have the flexiblity to be not just any instruction sequence (i.e., code bloat) but also junk bytes that can further cause anti-disassembly (i.e., disassembly desynchronization).

Our inserted opaque predicates' obfuscation is a deterministic and impossible instruction sequence. This is to allow us to detect our opaque predicates so we can evaluate them with deobfuscation tools. In practice, the obfuscation should not always be the same sequence (or else it is easily detected from the obfuscation). 

_Current tool implementation has some pitfalls (check <b>Other Notes and Pitfalls</b> section). A list of our TODOs can be found in [todos.md](todos.md)_

## Getting Started

#### Requirements
* Docker 

#### Installation (assumed in project root directory)
1. source helpers
2. buildc (will build a Docker image that contains everything you needed to run this tool)

#### To Run (assumed in project root directory)
* startc (assumed you ran `source helpers`. This command will drop you inside the Docker container)
* python3.10 src/insert\_ops.py [filepath to the folder containing target source code]
  * We assume your project root directory contains a folder called `dataset` and that folder will be mounted to the `\dataset` folder inside the container.
    * To change the location of the target source code to a folder other than `dataset`, you just have to change the `startc` command from the `helpers` file.
  * Make sure the folder containing target source code has the following additional files: 
    * `Makefile`: standard Makefile. The code will call `make` to compile the codebase after obfuscation. This is the default behavior but can be changed. 
    * `GNUmakefile`: a Makefile with instructions on how to run Frama-C for the specified codebase. The number of value sets that can be inferred heavily depend on the settings in this file.
  * if the program crashes, check out [debugging\_tips.md](debugging\_tips.md) for help

#### Settings
The followings are settings user can change:
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

## Other Notes and Pitfalls

* Cannot obfuscate code that contains recursive calls. This is a limitation of one of our dependencies, Frama-C
  * stated in [Frama-C's website under the "Technical Notes" section](https://www.frama-c.com/fc-plugins/eva.html).
* Target C file cannot use one-line for-loop, while-loop, or if statement. This is because the value set identified by Frama-C will be for the code inside scope of the one-liner, but the corresponding synthesized opaque predicate will be inserted outside scope of the one-liner. [Here is a more concrete explanation](problematic_oneliner_ex.md).
