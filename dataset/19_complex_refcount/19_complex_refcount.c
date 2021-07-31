#include "double_close.h"
#include <stdlib.h>
#include <stdio.h>

#ifndef s_FILES_DC_REFCOUNT
#define s_FILES_DC_REFCOUNT
void double_close_cont_init(FileCont* cont) {
    cont->refc = 1;
    cont->file = 0;
}

FileCont* double_close_cont_new() {
    FileCont* new_cont;

    new_cont = malloc(sizeof(FileCont));

    if(new_cont) {
        double_close_cont_init(new_cont);
    }
    return new_cont;
}

void double_close_cont_ref(FileCont* cont) {
    if(cont) {
        cont->refc++;
    }
}
void double_close_cont_unref(FileCont* cont) {
    if(cont->refc <= 1) {
        if(cont->file) fclose(cont->file);
    } else {
        cont->refc--;
    }
}

FILE* double_close_cont_get_file(FileCont* cont) {
    return cont->file;
}
void double_close_cont_set_file(FileCont* cont, FILE* file) {
    cont->file = file;
}
#endif //s_FILES_DC_REFCOUNT

#ifndef NO_MAIN
int main() {
    FileCont* cont;
    FILE* file;
    int val;

    file = fopen("file.txt", "r");
    if(!file) {
        return -1;
    }

    cont = double_close_cont_new();
    if(!cont) {
        fclose(file);
        return 1;
    }
    double_close_cont_set_file(cont, file);

    double_close_cont_ref(cont);
    double_close_cont_ref(cont);
    double_close_cont_unref(cont);
    double_close_cont_unref(cont);
    val = ((int) fgetc(double_close_cont_get_file(cont)));
    double_close_cont_unref(cont);
#ifndef NO_BUG
    double_close_cont_unref(cont);
#endif
    free(cont);

    printf("%i\n", val);

    return 1;
}
#endif
