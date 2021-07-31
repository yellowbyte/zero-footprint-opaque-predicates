#include <stdio.h>
#include <stdlib.h>
#include "double_close.h"

void double_close_if_else_int1(int x, int y) {
    int val = 0;
    FILE* file;

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
    double_close_if_else_int1(10, 10);
    double_close_if_else_int1(10, 11);
    double_close_if_else_int1(11, 11);
#else
    double_close_if_else_int1(10, 10); /* OK */
    double_close_if_else_int1(11, 12); /* DANGER */
    double_close_if_else_int1(11, 11); /* OK */
#endif

    return 1;
}
#endif
