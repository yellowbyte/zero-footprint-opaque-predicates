## Python Exception? 

To assist debugging, set `delete_metadata` to False.

Look inside the metadata folder (folder name will always start with "zfp-"): 
* Did a ".eva" folder get generated? If not, check that your GNUmakefile actually runs correctly
* Did a vsa.json file get generated? If not, the parsing of Frama-C output failed. Perhaps try setting `value_set_limit` to a smaller value

Did the program prematurely terminate before? If so, run `docker ps -a` and manually delete any leftover containers related to this projects.
