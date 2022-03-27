## Overview

[Zero Footprint Opaque Predicates](docs/README.md) obfuscate single-file C source code with opaque predicates that aim to syntactically and semantically resemble real predicates in order to prevent heuristic attacks (e.g., pattern matching) while maintaining resilience against automated attacks.

Currently, our inserted opaque predicates' obfuscation is a deterministic and impossible instruction sequence. This is to allow us to detect our opaque predicates so we can evaluate them with deobfuscation tools. In practice, the obfuscation should not always be the same sequence (or else it is easily detected from the obfuscation). 

## Getting Started

#### Requirements
* Docker 
* Linux

#### Installation (assumed in project root directory)
1. source scripts/zfpcmds
2. zfpbuild (will build a Docker image that contains everything you needed to run this tool)

#### To Run (assumed you ran `source scripts/zfpcmds`)
[Option 1]: `zfp <filepath to the folder containing target source code>`
* The use of our container is invisible to the user.

[Option 2]: `zfptest <filepath to the folder containing target source code>`
* This will drop user inside the Docker container and give user the ability to inspect or debug any potential errors when running the tool.
* To obfuscate from inside the container: `python3 zfp.py /tmp/<folder name of filepath to the folder containing target source code>`.

[Option 3]: `python3 zfp.py <filepath to the folder containing target source code>`
* This option allows user to use this tool without leveraging our container given that Frama-C, Rosette, jq, and Python version 3.10 or greater are installed.

For either one of the three options, the obfuscated binary will be placed in \<filepath to the folder containing target source code\>.

__NOTE__: Make sure the folder containing target source code has the following additional files: 
* `Makefile`: standard Makefile. The code will call `make` to compile the codebase after obfuscation. This is the default behavior but can be changed. [Here is a simple tutorial on how to write a Makefile](https://gist.github.com/yellowbyte/c23a6b25a4b3edf371777d21bd3dc7d0).
* `GNUmakefile`: a Makefile with instructions on how to run Frama-C for the specified codebase. The number of value sets that can be inferred heavily depend on the settings in this file. [Here is a simple tutorial on how to write the Frama-C tailored GNUmakefile](docs/framac_setup.md).
  * Our dependence on Frama-C also means that our tool cannot obfuscate code that contains recursive calls, [as it is a limitation of Frama-C](https://www.frama-c.com/fc-plugins/eva.html).

#### Settings
The followings are settings user can change:
* `--metadatadir <filepath>`: filepath to directory where metadata will be stored. Default to /tmp.
* `--delmetadata` or `--no-delmetadata`: decides whether to delete the metadata folder. Default to delete.
* `--limits <value>`: the max value set length to consider. Too small may lead to few synthesized opaque predicates. Too large may lead to crash. Default to 100000000. In our dataset, for example, "tweetnacl-usable" will fail with the default limits (change to 10000 instead). 

The option `-h` or `--help` will also give user information on the settings.

#### Examples
```bash
##### [Option 1]: with `zfp` #####
# if you want to inspect metadata, use `zfptest` and the `--no-delmetadata` option
yellowbyte:~/zero-footprint-opaque-predicates$ source scripts/zfpcmds 
yellowbyte:~/zero-footprint-opaque-predicates$ zfp --limits 30000 ./dataset/01_simple_if
...

##### [Option 2]: with `zfptest` #####
yellowbyte:~/zero-footprint-opaque-predicates$ source scripts/zfpcmds 
yellowbyte:~/zero-footprint-opaque-predicates$ zfptest ./dataset/01_simple_if
# inside Docker container
root@dfe5e978cd2b:/zfp# python3 zfp.py --no-delmetadata /tmp/01_simple_if
...
root@dfe5e978cd2b:/zfp# exit
# zfpstop to stop and remove container
yellowbyte:~/zero-footprint-opaque-predicates$ zfpstop

##### [Option 3]: running without using our container #####
yellowbyte:~/zero-footprint-opaque-predicates$ python3 zfp.py --no-delmetadata ./dataset/01_simple_if
...
```
