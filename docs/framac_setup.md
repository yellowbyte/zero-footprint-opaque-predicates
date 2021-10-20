## Frama-C Setup

[Frama-C](https://frama-c.com/) is a powerful program analysis tool. We use it in this project for its implementation of [abstract interpretation](https://www.di.ens.fr/~cousot/AI/IntroAbsInt.html). As for why we need to use abstract interpretation, check out [our project overview](https://github.com/yellowbyte/zero-footprint-opaque-predicates/blob/main/docs/debugging_tips.md).

[Here is a template to use for setting up Frama-C](docs/GNUmakefile_template). Simply change all occurrences of <filename> to the filename of the single C file (without the .c extension). 



Frama-C has some knobs to turn that allows user to tune its analysis. We plan to make another tutorial that explains some of the knobs for tuning the analysis in the future.  
