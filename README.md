## Overview

[Zero Footprint Opaque Predicates](docs/README.md) obfuscate single-file C source code with opaque predicates that aim to syntactically and semantically resemble real predicates in order to prevent heuristic attacks (e.g., pattern matching) while maintaining resilience against automated attacks.

Currently, our inserted opaque predicates' obfuscation is a deterministic and impossible instruction sequence. This is to allow us to detect our opaque predicates so we can evaluate them with deobfuscation tools. In practice, the obfuscation should not always be the same sequence (or else it is easily detected from the obfuscation). 

## Getting Started

#### Requirements
* Docker 
* Linux

#### Installation (assumed in project root directory)
1. source zfpcmds
2. zfpbuild (will build a Docker image that contains everything you needed to run this tool)

#### To Run (assumed you ran `source zfpcmds`)
* zfpstart [relative filepath to the folder containing target source code] 
  * This command will drop you inside the Docker container.
* python3.10 src/insert\_ops.py [relative filepath to the folder containing target source code]
  * If the program crashes, check out [debugging\_tips.md](docs/debugging\_tips.md) for help.

__NOTE__: Make sure the folder containing target source code has the following additional files: 
* `Makefile`: standard Makefile. The code will call `make` to compile the codebase after obfuscation. This is the default behavior but can be changed. [Here is a simple tutorial on how to write a Makefile](https://gist.github.com/yellowbyte/b2b61f547e51e80b30522a989e6ea88d).
* `GNUmakefile`: a Makefile with instructions on how to run Frama-C for the specified codebase. The number of value sets that can be inferred heavily depend on the settings in this file. [Here is a simple tutorial on how to write the GNUmakefile](docs/framac_setup.md).
  * Our dependence on Frama-C also means that our tool cannot obfuscate code that contains recursive calls, [as it is a limitation of Frama-C](https://www.frama-c.com/fc-plugins/eva.html).

#### Settings
The followings are settings user can change:
* `--metadatadir <path>`: path to directory where metadata will be stored. Default to /tmp
* `--delmetadata` or `--no-delmetadata`: decides whether to delete the metadata folder. Default to True
* `--limits <value>`: the max value set length to consider. Too small may lead to few synthesized opaque predicates. Too large may lead to crash. Default to 100000000
