#!/bin/bash 


# read json file in as a dictionary
declare -A vsas
while IFS="=" read -r key value
do
    vsas[$key]="$value"
done < <(jq -r "to_entries|map(\"\(.key)=\(.value)\")|.[]" $1)


# iterate each key in dictionary to try to synthesize an oapque predicate for it
# each key is of this format: loc:var_name
for key in "${!vsas[@]}"
do
    # remove array braces and change comma to empty space
    cur_vsa=$(echo "${vsas[$key]//,/ }" | tr -d '[],')

    # identify opaque predicate that always evaluate to false
    result=$(racket ./tools/rosette/synthesize.rkt f ${cur_vsa})
    if test "${result}" != "unsat"
    then
        comparator=$(echo ${result} | tr -d '()' | awk '{print $3}')
        constant=$(echo ${result} | tr -d '()' | awk '{print $4}')
        if test "${comparator}" == "#<procedure:neq?>"
        then 
            comparator="!="
        elif test "${comparator}" == "#<procedure:@eq?>"
        then 
            comparator="=="
        fi
        echo f ${key} ${comparator} ${constant}

        continue
    fi

    # if no opaquely falase predicate, identify opaque predicate that
    # always evaluate to true instead
    result=$(racket ./tools/rosette/synthesize.rkt t ${cur_vsa})
    if test "${result}" != "unsat"
    then
        comparator=$(echo ${result} | tr -d '()' | awk '{print $3}')
        constant=$(echo ${result} | tr -d '()' | awk '{print $4}')
        if test "${comparator}" == "#<procedure:neq?>"
        then 
            comparator="!="
        elif test "${comparator}" == "#<procedure:@eq?>"
        then 
            comparator="=="
        fi

        echo t ${key} ${comparator} ${constant}
    fi

    echo unsat ${key} ${vsas[$key]//,/ }
done
