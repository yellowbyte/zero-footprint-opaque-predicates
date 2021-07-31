#include <stdio.h>
#include <stdlib.h>
#include "double_close.h"

void double_close_if_else_int2(int x, int y) {
    FILE* file;
    int val = 0;
    int m, n;

    m = -1;
    n = 5;

    x = x*m+n;

#ifdef CATCH_BAD_PARAM
    if(x > 10 && x < y) {
        return;
    }
#endif

    file = fopen("file.txt","r");

    if(!file) {
        return;
    }

    if(x <= 10) {
        val = ((int) fgetc(file)) * 2;
    } else {
        val = (int) fgetc(file);
        fclose(file);
    }

    if(x >= y) {
        val += 37;
    } else {
        fclose(file);
    }

    if(x <= 10 && x >= y) {
        fclose(file);
    }

    printf("%i\n", val);
}

#ifndef NO_MAIN
int main() {
#ifdef NO_BUG
    double_close_if_else_int2(-5, 10);
    double_close_if_else_int2(-5, 11);
    double_close_if_else_int2(-6, 11);
#else
    double_close_if_else_int2(-5, 10); /* OK */
    double_close_if_else_int2(-6, 12); /* DANGER */
    double_close_if_else_int2(-6, 11); /* OK */
#endif

    return 1;
}
#endif
