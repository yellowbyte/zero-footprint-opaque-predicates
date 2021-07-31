#include <stdio.h>
#include <stdbool.h>
#include <stdlib.h>
#include "double_close.h"

void double_close_for(int x) {
    FILE* file;
    int val = 0;
    int i;

#ifdef CATCH_BAD_PARAM
    if(x < 10) {
        return;
    }
#endif

    file = fopen("file1.txt","r");

    if(!file) {
        return;
    }

    val = (int) fgetc(file);

    fclose(file);

    for(i = 0; i < 20; i++) {
        if(i > x) {
            fclose(file);
            file = fopen("file1.txt","r");
            if(!file) {
                return;
            }
            val += (int) fgetc(file);
        } else {
            val += 24;
        }
        if(i == 10) {
            file = fopen("file2.txt","r");
            if(!file) {
                return;
            }
        }
    }

    fclose(file);

    printf("%i\n", val);
}

#ifndef NO_MAIN
int main() {
#ifdef NO_BUG
    double_close_for(10);
#else
    double_close_for(9);
#endif

    return 1;
}
#endif
