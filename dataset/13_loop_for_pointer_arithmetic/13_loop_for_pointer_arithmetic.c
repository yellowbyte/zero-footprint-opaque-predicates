#include <stdlib.h>
#include <stdio.h>
#include "double_close.h"

static void initialize_array(FILE* ptr_arr[], int length) {
    int i;
    FILE** ptr = ptr_arr;

    for(i = 0; i < length; i++, ptr++) {
        *ptr = fopen("file.txt","r");
    }
}

static void close_backwards(FILE** ptr, int to_close) {
    int i;

    for(i = 0; i < to_close; i++, ptr--) {
        if(*ptr) fclose(*ptr);
    }
}

static void close_forwards(FILE** ptr, int to_close) {
    int i;

    for(i = 0; i < to_close; i++, ptr++) {
        if(*ptr) fclose(*ptr);
    }
}

void double_close_for_pointer(int x) {
    FILE* pointers[10];
    FILE** ptr;
    int val = 0, i;
    int to_close;

    if(x > 10) {
        return;
    }

#ifdef CATCH_BAD_PARAM
    if(x > 8) {
        return;
    }
#endif

    initialize_array(pointers, 10);

    close_backwards(pointers + 9, 2);

    ptr = pointers;
    for(int i = 0; i < 8; i++, ptr++) {
        if(*ptr) {
            val += (int) fgetc(*ptr);
        } else {
            val--;
        }
    }

    to_close = 8 - x;

    close_forwards(pointers, x);

    if(to_close > 0) {
        close_forwards(pointers + x, to_close);
    }

    printf("%i\n", val);
}

#ifndef NO_MAIN
int main() {
#ifdef NO_BUG
    double_close_for_pointer(4);
#else
    double_close_for_pointer(9);
#endif

    return 1;
}
#endif
