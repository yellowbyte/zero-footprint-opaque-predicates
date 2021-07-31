#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include "double_close.h"

void double_close_for_array(int x) {
    FILE* file = 0;
    int p[20];
    int val = 0;
    int i;

#ifdef CATCH_BAD_PARAM
    if(x != 19) {
        return;
    }
#endif

    file = fopen("file.txt","r");

    if(!file) {
        return;
    }

    val += ((int) fgetc(file));

    for(i = 0; i < 20; i++) {
        p[i] = 0;
    }
    p[x] = 1;

    for(i = 0; i < 20; i++) {
        if(p[i] == 1) {
            fclose(file);
        } else {
            fclose(file);
            file = fopen("file.txt","r");

            if(!file) {
                return;
            }
            val += ((int) fgetc(file)) + i;
        }
    }

    printf("%i\n", val);
}

#ifndef NO_MAIN
int main() {
#ifdef NO_BUG
    double_close_for_array(19);
#else
    double_close_for_array(10);
#endif

    return 1;
}
#endif
