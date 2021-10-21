## Frama-C Setup

[Frama-C](https://frama-c.com/) is a powerful program analysis tool. We use it in this project for its implementation of [abstract interpretation](https://www.di.ens.fr/~cousot/AI/IntroAbsInt.html). As for why we need to use abstract interpretation, check out [our project overview](README.md).

[Here is a template to use for setting up Frama-C](GNUmakefile_template). It is based on the GNUmakefile found in [Frama-C's open source case studies](https://git.frama-c.com/pub/open-source-case-studies). Simply change all occurrences of \<filename\> to the filename of the single C file (without the .c extension), rename the template to GNUmakefile, and place the template in the target source code folder.

Suppose your single C file is called "simple.c", to automate renaming use this command: `sed -i 's/<filename>/simple/g' GNUmakefile`

Frama-C has some knobs to turn that allows user to tune its analysis. We plan to make another tutorial that explains some of those knobs in the future.  
