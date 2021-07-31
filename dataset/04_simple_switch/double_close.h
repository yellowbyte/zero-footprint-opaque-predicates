#include <stdbool.h>
#include <stdio.h>

typedef struct _ResLeakRefCont FileCont;

struct _ResLeakRefCont {
    FILE* file;
    unsigned int refc;
};

void double_close_cont_init(FileCont* cont);
FileCont* double_close_cont_new();
void double_close_cont_ref(FileCont* cont);
void double_close_cont_unref(FileCont* cont);
FILE* double_close_cont_get_file(FileCont* cont);
void double_close_cont_set_file(FileCont* cont, FILE* file);

void double_close_for(int x);
void double_close_for_complex(int x);
void double_close_while_continue(int x);
void double_close_do_while_continue(int x);
void double_close_for_array(int x);
void double_close_for_pointer(int x);
void double_close_goto(int x);
void double_close_if_else(bool a, bool b);
void double_close_if_else_multi(bool a, bool b);
void double_close_if_else_int1(int x, int y);
void double_close_if_else_int2(int x, int y);
void double_close_pass_by_reference(bool a, bool b);
int double_close_switch(int x, int y);
int double_close_rec_multi(int x, int i, FILE** file_pt);
int double_close_rec(int x, int i, FILE** file_ptr);
int double_close_pseudo_rec1(int x, int y, int i, FILE** file_ptr);
int double_close_pseudo_rec2(int x, int y, int i, FILE** file_ptr);
void double_close_struct(int x, int y);
void double_close_function_pointer(bool a, bool b, int (*f)(FILE** dest, bool close_file));
void double_close_cross_file(bool a, bool b);
