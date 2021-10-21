## Python Exception? 

To assist debugging, set `--no-delmetadata`.

Look inside the metadata folder (folder name will always start with "zfp-"): 
* Did a ".eva" folder get generated? If not, check that your GNUmakefile actually runs correctly
* Did a vsa.json file get generated? If not, the parsing of Frama-C output failed. Perhaps try setting `value_set_limit` to a smaller value

If you ran this tool multiple times, multiple "zfp-" folders will be created. To find the most recent one that corresponds to your current exception: `ls -ltr`. The last listed "zfp-" folder will be the most recent one.
