#include <stdio.h>
#include <stdlib.h>
#include "double_close.h"

#ifndef s_NULLPOINTER_REFCOUNT
#define s_NULLPOINTER_REFCOUNT
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
        fclose(cont->file);
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
#endif //s_NULLPOINTER_REFCOUNT

void double_close_struct(int x, int y) {
    FileCont cont;
    FILE* file;
    int val = 78;

#ifdef CATCH_BAD_PARAM
    if(x > 10 && x <= y) {
        return;
    }
#endif

    file = fopen("file.txt","r");

    if(!file) {
        return;
    }

    double_close_cont_init(&cont);
    double_close_cont_set_file(&cont, file);

    val += (int) fgetc(file);

    if(x <= y) {
        fclose(double_close_cont_get_file(&cont));
    }

    if(x > 10) {
        fclose(file);
    } else {
        val = val * 2;
    }

    if(x > y && x <= 10) {
        fclose(double_close_cont_get_file(&cont));
    }

    printf("%i\n", val);
}

#ifndef NO_MAIN
int main() {
#ifdef NO_BUG
    double_close_struct(9, 10);
    double_close_struct(10, 11);
    double_close_struct(11, 10);
#else
    double_close_struct(11, 11); /* DANGER */
#endif

    return 1;
}
#endif
