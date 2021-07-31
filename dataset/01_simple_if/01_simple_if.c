#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include "double_close.h"

void double_close_if_else(bool a, bool b) {
    FILE* file;
    int val = 0;

#ifdef CATCH_BAD_PARAM
    if(!a & !b) {
        return;
    }
#endif

    file = fopen("file.txt","r");

    if(!file) {
        return;
    }

    if(a) {
        val = ((int) fgetc(file)) * 2;
    } else {
        val = (int) fgetc(file);
        fclose(file);
    }

    if(b) {
        val += 37;
    } else {
        fclose(file);
    }

    if(a & b) {
        fclose(file);
    }

    printf("%i\n", val);
}

#ifndef NO_MAIN
int main() {
#ifdef NO_BUG
    double_close_if_else(true, true);
    double_close_if_else(true, false);
    double_close_if_else(false, true);
#else
    double_close_if_else(true, true); /* OK */
    double_close_if_else(false, false); /* DANGER */
    double_close_if_else(false, true); /* OK */
#endif

    return 1;
}
#endif
