#ifndef JIM_MODULE_H_
#define JIM_MODULE_H_

#include <stdbool.h>
#include <stdlib.h>

typedef enum {
    JIM_ARRAY_SCOPE,
    JIM_OBJECT_SCOPE,
} Jim_Scope_Kind;

typedef struct {
    Jim_Scope_Kind kind;
    int tail;                   // Not the first element in an array or an object
    int key;                    // An object key was just placed
} Jim_Scope;

typedef struct {
    char *sink;
    size_t sink_count;
    size_t sink_capacity;
    Jim_Scope *scopes;
    size_t scopes_count;
    size_t scopes_capacity;
    size_t pp;
} Jim;

// ========================================

typedef enum {
    JIMP_INVALID,
    JIMP_EOF,

    // Puncts
    JIMP_OCURLY,
    JIMP_CCURLY,
    JIMP_OBRACKET,
    JIMP_CBRACKET,
    JIMP_COMMA,
    JIMP_COLON,

    // Symbols
    JIMP_TRUE,
    JIMP_FALSE,
    JIMP_NULL,

    // Values
    JIMP_STRING,
    JIMP_NUMBER,
} Jimp_Token;

typedef struct {
    const char *file_path;
    const char *start;
    const char *end;
    const char *point;

    Jimp_Token token;
    const char *token_start;    // TODO: `token_start` is primarily used for diagnostics location. Rename it accordingly.

    char *string;
    size_t string_count;
    size_t string_capacity;
    double number;
    bool boolean;
} Jimp;

// ========================================

typedef struct JimModule {
    void (*begin)(Jim *jim);
    void (*null)(Jim *jim);
    void (*boolean)(Jim *jim, int boolean);
    void (*integer)(Jim *jim, long long int x);
    void (*floating)(Jim *jim, double x, int precision);
    void (*string)(Jim *jim, const char *str);
    void (*string_sized)(Jim *jim, const char *str, size_t size);
    void (*element_begin)(Jim *jim);
    void (*element_end)(Jim *jim);
    void (*array_begin)(Jim *jim);
    void (*array_end)(Jim *jim);
    void (*object_begin)(Jim *jim);
    void (*member_key)(Jim *jim, const char *str);
    void (*member_key_sized)(Jim *jim, const char *str, size_t size);
    void (*object_end)(Jim *jim);
} JimModule;

typedef struct JimpModule {
    void (*begin)(Jimp *jimp, const char *file_path, const char *input, size_t input_size);
    bool (*boolean)(Jimp *jimp);
    bool (*number)(Jimp *jimp);
    bool (*string)(Jimp *jimp);
    bool (*object_begin)(Jimp *jimp);
    bool (*object_member)(Jimp *jimp);
    bool (*object_end)(Jimp *jimp);
    void (*unknown_member)(Jimp *jimp);
    bool (*array_begin)(Jimp *jimp);
    bool (*array_item)(Jimp *jimp);
    bool (*array_end)(Jimp *jimp);
    void (*diagf)(Jimp *jimp, const char *fmt, ...);
    bool (*is_null_ahead)(Jimp *jimp);
    bool (*is_bool_ahead)(Jimp *jimp);
    bool (*is_number_ahead)(Jimp *jimp);
    bool (*is_string_ahead)(Jimp *jimp);
    bool (*is_array_ahead)(Jimp *jimp);
    bool (*is_object_ahead)(Jimp *jimp);
} JimpModule;

JimModule* import_JimModule(const char* path);
JimpModule* import_JimpModule(const char* path);

#endif
// --------------------------------------------------
#ifdef JIM_MODULE_IMPLEMENTATION

#include "pll.h"
#include <stdio.h>

static Lib jim_lib = {0};

static JimModule jim_module = {0};
static JimpModule jimp_module = {0};

#define JimModule_LOG(fmt, ...) \
        fprintf(stderr, "[JimModule] " fmt "\n" __VA_ARGS__)

static bool check_module(void* module, size_t module_size){
    void** module_a = (void**)module; 
    for (size_t i = 0; i < module_size; i++)
        if(module_a[i] == NULL)return false;
    return true;
} 

JimModule* import_JimModule(const char* path){
    if(check_module(&jim_module, sizeof(JimModule)/sizeof(void*))) return &jim_module;
    jim_lib.path = path;
    
    jim_module.begin = (void (*)(Jim *))pll_get(&jim_lib, "jim_begin");
    if(!jim_module.begin){
        JimModule_LOG("jim_module.jim_begin is NULL!");
        return NULL;
    }
    jim_module.null = (void (*)(Jim *))pll_get(&jim_lib, "jim_null");
    if(!jim_module.null){
        JimModule_LOG("jim_module.jim_null is NULL!");
        return NULL;
    }
    jim_module.boolean = (void (*)(Jim *, int))pll_get(&jim_lib, "jim_bool");
    if(!jim_module.boolean){
        JimModule_LOG("jim_module.jim_bool is NULL!");
        return NULL;
    }
    jim_module.integer = (void (*)(Jim *, long long int))pll_get(&jim_lib, "jim_integer");
    if(!jim_module.integer){
        JimModule_LOG("jim_module.jim_integer is NULL!");
        return NULL;
    }
    jim_module.floating = (void (*)(Jim *, double, int))pll_get(&jim_lib, "jim_float");
    if(!jim_module.floating){
        JimModule_LOG("jim_module.jim_float is NULL!");
        return NULL;
    }
    jim_module.string = (void (*)(Jim *, const char *))pll_get(&jim_lib, "jim_string");
    if(!jim_module.string){
        JimModule_LOG("jim_module.jim_string is NULL!");
        return NULL;
    }
    jim_module.string_sized = (void (*)(Jim *, const char *, size_t))pll_get(&jim_lib, "jim_string_sized");
    if(!jim_module.string_sized){
        JimModule_LOG("jim_module.jim_string_sized is NULL!");
        return NULL;
    }
    jim_module.element_begin = (void (*)(Jim *))pll_get(&jim_lib, "jim_element_begin");
    if(!jim_module.element_begin){
        JimModule_LOG("jim_module.jim_element_begin is NULL!");
        return NULL;
    }
    jim_module.element_end = (void (*)(Jim *))pll_get(&jim_lib, "jim_element_end");
    if(!jim_module.element_end){
        JimModule_LOG("jim_module.jim_element_end is NULL!");
        return NULL;
    }
    jim_module.array_begin = (void (*)(Jim *))pll_get(&jim_lib, "jim_array_begin");
    if(!jim_module.array_begin){
        JimModule_LOG("jim_module.jim_array_begin is NULL!");
        return NULL;
    }
    jim_module.array_end = (void (*)(Jim *))pll_get(&jim_lib, "jim_array_end");
    if(!jim_module.array_end){
        JimModule_LOG("jim_module.jim_array_end is NULL!");
        return NULL;
    }
    jim_module.object_begin = (void (*)(Jim *))pll_get(&jim_lib, "jim_object_begin");
    if(!jim_module.object_begin){
        JimModule_LOG("jim_module.jim_object_begin is NULL!");
        return NULL;
    }
    jim_module.member_key = (void (*)(Jim *, const char *))pll_get(&jim_lib, "jim_member_key");
    if(!jim_module.member_key){
        JimModule_LOG("jim_module.jim_member_key is NULL!");
        return NULL;
    }
    jim_module.member_key_sized = (void (*)(Jim *, const char *, size_t))pll_get(&jim_lib, "jim_member_key_sized");
    if(!jim_module.member_key_sized){
        JimModule_LOG("jim_module.jim_member_key_sized is NULL!");
        return NULL;
    }
    jim_module.object_end = (void (*)(Jim *))pll_get(&jim_lib, "jim_object_end");
    if(!jim_module.object_end){
        JimModule_LOG("jim_module.jim_object_end is NULL!");
        return NULL;
    }

    return &jim_module;
}

JimpModule* import_JimpModule(const char* path){
    if(check_module(&jimp_module, sizeof(JimpModule)/sizeof(void*))) return &jimp_module;
    jim_lib.path = path;

    jimp_module.begin = (void (*)(Jimp *, const char *, const char *, size_t))pll_get(&jim_lib, "jimp_begin");
    if(!jimp_module.begin){
        JimModule_LOG("jimp_module.jimp_begin is NULL");
        return NULL;
    }
    jimp_module.boolean = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_bool");
    if(!jimp_module.boolean){
        JimModule_LOG("jimp_module.jimp_bool is NULL");
        return NULL;
    }
    jimp_module.number = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_number");
    if(!jimp_module.number){
        JimModule_LOG("jimp_module.jimp_number is NULL");
        return NULL;
    }
    jimp_module.string = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_string");
    if(!jimp_module.string){
        JimModule_LOG("jimp_module.jimp_string is NULL");
        return NULL;
    }
    jimp_module.object_begin = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_object_begin");
    if(!jimp_module.object_begin){
        JimModule_LOG("jimp_module.jimp_object_begin is NULL");
        return NULL;
    }
    jimp_module.object_member = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_object_member");
    if(!jimp_module.object_member){
        JimModule_LOG("jimp_module.jimp_object_member is NULL");
        return NULL;
    }
    jimp_module.object_end = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_object_end");
    if(!jimp_module.object_end){
        JimModule_LOG("jimp_module.jimp_object_end is NULL");
        return NULL;
    }
    jimp_module.unknown_member = (void (*)(Jimp *))pll_get(&jim_lib, "jimp_unknown_member");
    if(!jimp_module.unknown_member){
        JimModule_LOG("jimp_module.jimp_unknown_member is NULL");
        return NULL;
    }
    jimp_module.array_begin = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_array_begin");
    if(!jimp_module.array_begin){
        JimModule_LOG("jimp_module.jimp_array_begin is NULL");
        return NULL;
    }
    jimp_module.array_item = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_array_item");
    if(!jimp_module.array_item){
        JimModule_LOG("jimp_module.jimp_array_item is NULL");
        return NULL;
    }
    jimp_module.array_end = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_array_end");
    if(!jimp_module.array_end){
        JimModule_LOG("jimp_module.jimp_array_end is NULL");
        return NULL;
    }
    jimp_module.diagf = (void (*)(Jimp *, const char *, ...))pll_get(&jim_lib, "jimp_diagf");
    if(!jimp_module.diagf){
        JimModule_LOG("jimp_module.jimp_diagf is NULL");
        return NULL;
    }
    jimp_module.is_null_ahead = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_is_null_ahead");
    if(!jimp_module.is_null_ahead){
        JimModule_LOG("jimp_module.jimp_is_null_ahead is NULL");
        return NULL;
    }
    jimp_module.is_bool_ahead = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_is_bool_ahead");
    if(!jimp_module.is_bool_ahead){
        JimModule_LOG("jimp_module.jimp_is_bool_ahead is NULL");
        return NULL;
    }
    jimp_module.is_number_ahead = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_is_number_ahead");
    if(!jimp_module.is_number_ahead){
        JimModule_LOG("jimp_module.jimp_is_number_ahead is NULL");
        return NULL;
    }
    jimp_module.is_string_ahead = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_is_string_ahead");
    if(!jimp_module.is_string_ahead){
        JimModule_LOG("jimp_module.jimp_is_string_ahead is NULL");
        return NULL;
    }
    jimp_module.is_array_ahead = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_is_array_ahead");
    if(!jimp_module.is_array_ahead){
        JimModule_LOG("jimp_module.jimp_is_array_ahead is NULL");
        return NULL;
    }
    jimp_module.is_object_ahead = (bool (*)(Jimp *))pll_get(&jim_lib, "jimp_is_object_ahead");
    if(!jimp_module.is_object_ahead){
        JimModule_LOG("jimp_module.jimp_is_object_ahead is NULL");
        return NULL;
    }

    return &jimp_module;
}

#endif