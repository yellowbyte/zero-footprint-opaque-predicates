#include <stdio.h>
#include <stdlib.h>
#include "double_close.h"

void double_close_goto(int x) {
    FILE* file = 0;
    int val = 0;
    int i = 0;

    if(i > x) {
        return;
    }

#ifdef CATCH_BAD_PARAM
    if(x > 0) {
        return;
    }
#endif

    file = fopen("file.txt","r");

    if(!file) {
        return;
    }

    val += (int) fgetc(file);

GOTO_LABEL:
    if(i <= x) {
        fclose(file);
    } else {
        printf("%i\n", val);
    }

    if(i == 0) {
        i++;
        goto GOTO_LABEL;
    }
}

#ifndef NO_MAIN
int main() {
#ifdef NO_BUG
    double_close_goto(0);
#else
    double_close_goto(1);
#endif

    return 1;
}
#endif
