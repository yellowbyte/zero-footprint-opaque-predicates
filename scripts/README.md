## Files 

* `BinValueSetEval.py`: given an obfuscated binary, check if binary abstract interpretation (available in BinaryNinja) can identify our opaque predicates by evaluating variable's value set under the corresponding predicate
* `zfpid.py`: print all the opaque predicates locations
  * We purposely make our opaque predicates' obfuscation (i.e., injected non-executable code) deterministic so we can detect them for evaluation with other deobfuscation tools
* `getstats.py`: given a file containing the correct opaque predicates locations (can be retrieved with zfpid.py) and another file containing the opaque predicates locations identified by a deobfuscation tool, evaluate how well the deobfuscation tool performs
* `zfpcmds`: a host of bash functions to build, and, and clean up this project
* `devcmds`: a host of bash functions to aide development
* `autocmds`: a host of bash functions to help perform evaluations/obfuscations on multiple binaries
  * run this command to use: source scripts/autoeval
