#include <stdio.h>
#include <stdlib.h>
#include "double_close.h"

int double_close_pseudo_rec1(int x, int y, int i, FILE** file_ptr) {
    int val;
#ifdef CATCH_BAD_PARAM
    if(x >= y && x < 10) {
        return -1;
    }
#endif

    if(!*file_ptr) {
        return -1;
    }

    val = ((int) fgetc(*file_ptr));

    if(i > 0) {
        fclose(*file_ptr);
        return 37;
    }

    if(x < y) {
        fclose(*file_ptr);
    } else {
        fgetc(*file_ptr);
    }

    return val + double_close_pseudo_rec2(x, y, 1, file_ptr);
}

int double_close_pseudo_rec2(int x, int y, int i, FILE** file_ptr) {
    int val = 78;
    if(i > 0) {
        if(x < 10) {
            fclose(*file_ptr);
        } else {
            val += 2;
        }

        if(x >= y && x >= 10) {
            fclose(*file_ptr);
            *file_ptr = 0;
        }
        return val;
    }

    return 5 + double_close_pseudo_rec1(x, y, 1, file_ptr);
}

#ifndef NO_MAIN
int main() {
    FILE* file = fopen("file.txt", "r");
#ifdef NO_BUG
    printf("%i\n", double_close_pseudo_rec1(9, 10, 0, &file));
    file = fopen("file.txt", "r");
    printf("%i\n", double_close_pseudo_rec1(11, 10, 0, &file));
#else
    printf("%i\n", double_close_pseudo_rec1(9, 8, 0, &file));
#endif

    return 1;
}
#endif
