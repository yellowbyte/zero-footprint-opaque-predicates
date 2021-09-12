1. Experiments with other source-level abstract interpretation tools (e.g., [Apron](https://github.com/antoinemine/apron), [MOPSA](https://mopsa.lip6.fr), [clam](https://github.com/seahorn/clam)) and combine their outputs with Frama-C's value analysis output. 
2. Add option to choose from various kinds of opaque predicates' obfuscation (e.g., junk bytes, random branch)
3. Add support to insert opaque predicates into multi-files project.
4. Add option to remove opaque predicates that are detected by automated tools so that the remaining opaque predicates have higher resilience.
