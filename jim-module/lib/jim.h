// Jim 2.0
//
// Current version of Jim. Main differences from Jim 1.0 are
// - Using Dynamic Arrays for scopes allowing them to be arbitrarily nested,
// - Collecting the output into a sink which is a String Builder now, delegating all the IO hustle to the user of the library,
// - Lack of Jim_Error mechanism, which dealt with IO errors and invalid usage of the API. Since we don't deal with IO anymore we have no IO errors. And invalid usage of the API is simply assert()-ed.

#ifndef JIM_H_
#define JIM_H_

#ifndef JIM_SCOPES_CAPACITY
#define JIM_SCOPES_CAPACITY 128
#endif // JIM_SCOPES_CAPACITY

#include <assert.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>

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

void jim_begin(Jim *jim);
void jim_null(Jim *jim);
void jim_bool(Jim *jim, int boolean);
void jim_integer(Jim *jim, long long int x);
// TODO: deprecate this version of jim_float introduce the one that does not require precision and uses something like sprintf from libc to render the floats
void jim_float(Jim *jim, double x, int precision);
void jim_string(Jim *jim, const char *str);
void jim_string_sized(Jim *jim, const char *str, size_t size);

void jim_element_begin(Jim *jim);
void jim_element_end(Jim *jim);

void jim_array_begin(Jim *jim);
void jim_array_end(Jim *jim);

void jim_object_begin(Jim *jim);
void jim_member_key(Jim *jim, const char *str);
void jim_member_key_sized(Jim *jim, const char *str, size_t size);
void jim_object_end(Jim *jim);

#endif // JIM_H_

#ifdef JIM_IMPLEMENTATION

static void jim_scope_push(Jim *jim, Jim_Scope_Kind kind)
{
    if (jim->scopes_count >= jim->scopes_capacity) {
        if (jim->scopes_capacity == 0) jim->scopes_capacity = JIM_SCOPES_CAPACITY;
        else jim->scopes_capacity *= 2;
        jim->scopes = realloc(jim->scopes, sizeof(*jim->scopes)*jim->scopes_capacity);
        assert(jim->scopes);
    }
    jim->scopes[jim->scopes_count].kind = kind;
    jim->scopes[jim->scopes_count].tail = 0;
    jim->scopes[jim->scopes_count].key = 0;
    jim->scopes_count += 1;
}

static void jim_scope_pop(Jim *jim)
{
    assert(jim->scopes_count > 0);
    jim->scopes_count--;
}

static Jim_Scope *jim_current_scope(Jim *jim)
{
    if (jim->scopes_count > 0) {
        return &jim->scopes[jim->scopes_count - 1];
    }
    return NULL;
}

static void jim_write(Jim *jim, const char *buffer, size_t size)
{
    while (jim->sink_count + size >= jim->sink_capacity) {
        // TODO: rename JIM_SCOPES_CAPACITY to something else since it's used by both sink and scopes
        if (jim->sink_capacity == 0) jim->sink_capacity = JIM_SCOPES_CAPACITY;
        else jim->sink_capacity *= 2;
        jim->sink = realloc(jim->sink, sizeof(*jim->sink)*jim->sink_capacity);
    }
    memcpy(jim->sink + jim->sink_count, buffer, size);
    jim->sink_count += size;
}

static void jim_write_cstr(Jim *jim, const char *cstr)
{
    jim_write(jim, cstr, strlen(cstr));
}

static int jim_get_utf8_char_len(unsigned char ch)
{
    if ((ch & 0x80) == 0) return 1;
    switch (ch & 0xf0) {
        case 0xf0:
            return 4;
        case 0xe0:
            return 3;
        default:
            return 2;
    }
}

void jim_begin(Jim *jim)
{
    jim->sink_count = 0;
    jim->scopes_count = 0;
}

void jim_element_begin(Jim *jim)
{
    Jim_Scope *scope = jim_current_scope(jim);
    if (scope) {
        if (scope->tail && !scope->key) {
            jim_write_cstr(jim, ",");
        }
        if (jim->pp) {
            if (scope->key) {
                jim_write_cstr(jim, " ");
            } else {
                jim_write_cstr(jim, "\n");
                for (size_t i = 0; i < jim->scopes_count*jim->pp; ++i) {
                    jim_write_cstr(jim, " ");
                }
            }
        }
    }
}

void jim_element_end(Jim *jim)
{
    Jim_Scope *scope = jim_current_scope(jim);
    if (scope) {
        scope->tail = 1;
        scope->key = 0;
    }
}

void jim_null(Jim *jim)
{
    jim_element_begin(jim);
    jim_write_cstr(jim, "null");
    jim_element_end(jim);
}

void jim_bool(Jim *jim, int boolean)
{
    jim_element_begin(jim);
    if (boolean) {
        jim_write_cstr(jim, "true");
    } else {
        jim_write_cstr(jim, "false");
    }
    jim_element_end(jim);
}

static void jim_integer_no_element(Jim *jim, long long int x)
{
    if (x < 0) {
        jim_write_cstr(jim, "-");
        x = -x;
    }

    if (x == 0) {
        jim_write_cstr(jim, "0");
    } else {
        char buffer[64];
        size_t count = 0;

        while (x > 0) {
            buffer[count++] = (x % 10) + '0';
            x /= 10;
        }

        for (size_t i = 0; i < count / 2; ++i) {
            char t = buffer[i];
            buffer[i] = buffer[count - i - 1];
            buffer[count - i - 1] = t;
        }

        jim_write(jim, buffer, count);
    }
}

void jim_integer(Jim *jim, long long int x)
{
    jim_element_begin(jim);
    jim_integer_no_element(jim, x);
    jim_element_end(jim);
}

static int is_nan_or_inf(double x)
{
    unsigned long long int mask = (1ULL << 11ULL) - 1ULL;
    return (((*(unsigned long long int*) &x) >> 52ULL) & mask) == mask;
}

void jim_float(Jim *jim, double x, int precision)
{
    if (is_nan_or_inf(x)) {
        jim_null(jim);
    } else {
        jim_element_begin(jim);

        jim_integer_no_element(jim, (long long int) x);
        x -= (double) (long long int) x;
        while (precision-- > 0) {
            x *= 10.0;
        }
        jim_write_cstr(jim, ".");

        long long int y = (long long int) x;
        if (y < 0) {
            y = -y;
        }
        jim_integer_no_element(jim, y);

        jim_element_end(jim);
    }
}

static void jim_string_sized_no_element(Jim *jim, const char *str, size_t size)
{
    const char *hex_digits = "0123456789abcdef";
    const char *specials = "btnvfr";
    const char *p = str;
    size_t len = size;

    jim_write_cstr(jim, "\"");
    size_t cl;
    for (size_t i = 0; i < len; i++) {
        unsigned char ch = ((unsigned char *) p)[i];
        if (ch == '"' || ch == '\\') {
            jim_write(jim, "\\", 1);
            jim_write(jim, p + i, 1);
        } else if (ch >= '\b' && ch <= '\r') {
            jim_write(jim, "\\", 1);
            jim_write(jim, &specials[ch - '\b'], 1);
        } else if (0x20 <= ch && ch <= 0x7F) { // is printable
            jim_write(jim, p + i, 1);
        } else if ((cl = jim_get_utf8_char_len(ch)) == 1) {
            jim_write(jim, "\\u00", 4);
            jim_write(jim, &hex_digits[(ch >> 4) % 0xf], 1);
            jim_write(jim, &hex_digits[ch % 0xf], 1);
        } else {
            jim_write(jim, p + i, cl);
            i += cl - 1;
        }
    }

    jim_write_cstr(jim, "\"");
}

void jim_string_sized(Jim *jim, const char *str, size_t size)
{
    jim_element_begin(jim);
    jim_string_sized_no_element(jim, str, size);
    jim_element_end(jim);
}

void jim_string(Jim *jim, const char *str)
{
    jim_string_sized(jim, str, strlen(str));
}

void jim_array_begin(Jim *jim)
{
    jim_element_begin(jim);
    jim_write_cstr(jim, "[");
    jim_scope_push(jim, JIM_ARRAY_SCOPE);
}


void jim_array_end(Jim *jim)
{
    Jim_Scope *scope = jim_current_scope(jim);
    if (jim->pp && scope && scope->tail) {
        jim_write_cstr(jim, "\n");
        for (size_t i = 0; i < (jim->scopes_count - 1)*jim->pp; ++i) {
            jim_write_cstr(jim, " ");
        }
    }
    jim_write_cstr(jim, "]");
    jim_scope_pop(jim);
    jim_element_end(jim);
}

void jim_object_begin(Jim *jim)
{
    jim_element_begin(jim);
    jim_write_cstr(jim, "{");
    jim_scope_push(jim, JIM_OBJECT_SCOPE);
}

void jim_member_key(Jim *jim, const char *str)
{
    jim_member_key_sized(jim, str, strlen(str));
}

void jim_member_key_sized(Jim *jim, const char *str, size_t size)
{
    jim_element_begin(jim);
    Jim_Scope *scope = jim_current_scope(jim);
    assert(scope);
    assert(scope->kind == JIM_OBJECT_SCOPE);
    assert(!scope->key);
    jim_string_sized_no_element(jim, str, size);
    jim_write_cstr(jim, ":");
    scope->key = 1;
}

void jim_object_end(Jim *jim)
{
    Jim_Scope *scope = jim_current_scope(jim);
    if (jim->pp && scope && scope->tail) {
        jim_write_cstr(jim, "\n");
        for (size_t i = 0; i < (jim->scopes_count - 1)*jim->pp; ++i) {
            jim_write_cstr(jim, " ");
        }
    }
    jim_write_cstr(jim, "}");
    jim_scope_pop(jim);
    jim_element_end(jim);
}

#endif // JIM_IMPLEMENTATION
// Prototype of an Immediate Deserialization idea. Expect this API to change a lot.
#ifndef JIMP_H_
#define JIMP_H_

#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stdarg.h>
#include <string.h>
#include <ctype.h>

// TODO: move all diagnostics reporting outside of the library
//   So the user has more options on how to report things

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

// TODO: how do null-s fit into this entire system?

void jimp_begin(Jimp *jimp, const char *file_path, const char *input, size_t input_size);

/// If succeeds puts the freshly parsed boolean into jimp->boolean.
/// Any consequent calls to the jimp_* functions may invalidate jimp->boolean.
bool jimp_bool(Jimp *jimp);

/// If succeeds puts the freshly parsed number into jimp->number.
/// Any consequent calls to the jimp_* functions may invalidate jimp->number.
bool jimp_number(Jimp *jimp);

/// If succeeds puts the freshly parsed string into jimp->string as a NULL-terminated string.
/// Any consequent calls to the jimp_* functions may invalidate jimp->string.
/// strdup it if you don't wanna lose it (memory management is on you at that point).
bool jimp_string(Jimp *jimp);

/// Parses the beginning of the object `{`
bool jimp_object_begin(Jimp *jimp);

/// If succeeds puts the key of the member into jimp->string as a NULL-terminated string.
/// Any consequent calls to the jimp_* functions may invalidate jimp->string.
/// strdup it if you don't wanna lose it (memory management is on you at that point).
bool jimp_object_member(Jimp *jimp);

/// Parses the end of the object `}`
bool jimp_object_end(Jimp *jimp);

/// Reports jimp->string as an unknown member. jimp->string is expected to be populated by
/// jimp_object_member.
void jimp_unknown_member(Jimp *jimp);

/// Parses the beginning of the array `[`
bool jimp_array_begin(Jimp *jimp);

/// Checks whether there is any more items in the array.
bool jimp_array_item(Jimp *jimp);

/// Parses the end of the array `]`
bool jimp_array_end(Jimp *jimp);

/// Prints diagnostic at the current position of the parser.
void jimp_diagf(Jimp *jimp, const char *fmt, ...);

bool jimp_is_null_ahead(Jimp *jimp);
bool jimp_is_bool_ahead(Jimp *jimp);
bool jimp_is_number_ahead(Jimp *jimp);
bool jimp_is_string_ahead(Jimp *jimp);
bool jimp_is_array_ahead(Jimp *jimp);
bool jimp_is_object_ahead(Jimp *jimp);

#endif // JIMP_H_

#ifdef JIMP_IMPLEMENTATION

static bool jimp__expect_token(Jimp *jimp, Jimp_Token token);
static bool jimp__get_and_expect_token(Jimp *jimp, Jimp_Token token);
static const char *jimp__token_kind(Jimp_Token token);
static bool jimp__get_token(Jimp *jimp);
static void jimp__skip_whitespaces(Jimp *jimp);
static void jimp__append_to_string(Jimp *jimp, char x);

static void jimp__append_to_string(Jimp *jimp, char x)
{
    if (jimp->string_count >= jimp->string_capacity) {
        if (jimp->string_capacity == 0) jimp->string_capacity = 1024;
        else jimp->string_capacity *= 2;
        jimp->string = realloc(jimp->string, jimp->string_capacity);
    }
    jimp->string[jimp->string_count++] = x;
}

static void jimp__skip_whitespaces(Jimp *jimp)
{
    while (jimp->point < jimp->end && isspace(*jimp->point)) {
        jimp->point += 1;
    }
}

static Jimp_Token jimp__puncts[256] = {
    ['{'] = JIMP_OCURLY,
    ['}'] = JIMP_CCURLY,
    ['['] = JIMP_OBRACKET,
    [']'] = JIMP_CBRACKET,
    [','] = JIMP_COMMA,
    [':'] = JIMP_COLON,
};

static struct {
    Jimp_Token token;
    const char *symbol;
} jimp__symbols[] = {
    { .token = JIMP_TRUE,  .symbol = "true"  },
    { .token = JIMP_FALSE, .symbol = "false" },
    { .token = JIMP_NULL,  .symbol = "null"  },
};
#define jimp__symbols_count (sizeof(jimp__symbols)/sizeof(jimp__symbols[0]))

static bool jimp__get_token(Jimp *jimp)
{
    jimp__skip_whitespaces(jimp);

    jimp->token_start = jimp->point;

    if (jimp->point >= jimp->end) {
        jimp->token = JIMP_EOF;
        return false;
    }

    jimp->token = jimp__puncts[(unsigned char)*jimp->point];
    if (jimp->token) {
        jimp->point += 1;
        return true;
    }

    for (size_t i = 0; i < jimp__symbols_count; ++i) {
        const char *symbol = jimp__symbols[i].symbol;
        if (*symbol == *jimp->point) {
            while (*symbol && jimp->point < jimp->end && *symbol++ == *jimp->point++) {}
            if (*symbol) {
                jimp->token = JIMP_INVALID;
                jimp_diagf(jimp, "ERROR: invalid symbol\n");
                return false;
            } else {
                jimp->token = jimp__symbols[i].token;
                return true;
            }
        }
    }

    char *endptr = NULL;
    jimp->number = strtod(jimp->point, &endptr); // TODO: This implies that jimp->end is a valid address and *jimp->end == 0
    if (jimp->point != endptr) {
        jimp->point = endptr;
        jimp->token = JIMP_NUMBER;
        return true;
    }

    if (*jimp->point == '"') {
        jimp->point++;
        jimp->string_count = 0;
        while (jimp->point < jimp->end) {
            // TODO: support all the JSON escape sequences defined in the spec
            // Yes, including those dumb suroggate pairs. Spec is spec.
            switch (*jimp->point) {
                case '\\': {
                    jimp->point++;
                    if (jimp->point >= jimp->end) {
                        jimp->token_start = jimp->point;
                        jimp_diagf(jimp, "ERROR: unfinished escape sequence\n");
                        return false;
                    }
                    switch (*jimp->point) {
                        case 'r':
                            jimp->point++;
                            jimp__append_to_string(jimp, '\r');
                            break;
                        case 'n':
                            jimp->point++;
                            jimp__append_to_string(jimp, '\n');
                            break;
                        case 't':
                            jimp->point++;
                            jimp__append_to_string(jimp, '\t');
                            break;
                        case '\\':
                            jimp->point++;
                            jimp__append_to_string(jimp, '\\');
                            break;
                        case '"':
                            jimp->point++;
                            jimp__append_to_string(jimp, '"');
                            break;
                        default:
                            jimp->token_start = jimp->point;
                            jimp_diagf(jimp, "ERROR: invalid escape sequence\n");
                            return false;
                    }
                    break;
                }
                        case '"': {
                            jimp->point++;
                            jimp__append_to_string(jimp, '\0');
                            jimp->token = JIMP_STRING;
                            return true;
                        }
                        default: {
                            char x = *jimp->point++;
                            jimp__append_to_string(jimp, x);
                        }
            }
        }
        jimp->token = JIMP_INVALID;
        jimp_diagf(jimp, "ERROR: unfinished string\n");
        return false;
    }

    jimp->token = JIMP_INVALID;
    jimp_diagf(jimp, "ERROR: invalid token\n");
    return false;
}

void jimp_begin(Jimp *jimp, const char *file_path, const char *input, size_t input_size)
{
    jimp->file_path = file_path;
    jimp->start     = input;
    jimp->end       = input + input_size;
    jimp->point     = input;
}

void jimp_diagf(Jimp *jimp, const char *fmt, ...)
{
    long line_number = 0;
    const char *line_start = jimp->start;
    const char *point = jimp->start;
    while (point < jimp->token_start) {
        char x = *point++;
        if (x == '\n') {
            line_start = point;
            line_number += 1;
        }
    }

    fprintf(stderr, "%s:%ld:%ld: ", jimp->file_path, line_number + 1, point - line_start + 1);
    va_list args;
    va_start(args, fmt);
    vfprintf(stderr, fmt, args);
    va_end(args);
}

static const char *jimp__token_kind(Jimp_Token token)
{
    switch (token) {
        case JIMP_EOF:      return "end of input";
        case JIMP_INVALID:  return "invalid";
        case JIMP_OCURLY:   return "{";
        case JIMP_CCURLY:   return "}";
        case JIMP_OBRACKET: return "[";
        case JIMP_CBRACKET: return "]";
        case JIMP_COMMA:    return ",";
        case JIMP_COLON:    return ":";
        case JIMP_TRUE:     return "true";
        case JIMP_FALSE:    return "false";
        case JIMP_NULL:     return "null";
        case JIMP_STRING:   return "string";
        case JIMP_NUMBER:   return "number";
    }
    assert(0 && "unreachable");
    return NULL;
}

bool jimp_array_begin(Jimp *jimp)
{
    return jimp__get_and_expect_token(jimp, JIMP_OBRACKET);
}

bool jimp_array_end(Jimp *jimp)
{
    return jimp__get_and_expect_token(jimp, JIMP_CBRACKET);
}

bool jimp_array_item(Jimp *jimp)
{
    const char *point = jimp->point;
    if (!jimp__get_token(jimp)) return false;
    if (jimp->token == JIMP_COMMA) return true;
    if (jimp->token == JIMP_CBRACKET) {
        jimp->point = point;
        return false;
    }
    jimp->point = point;
    return true;
}

void jimp_unknown_member(Jimp *jimp)
{
    jimp_diagf(jimp, "ERROR: unexpected object member `%s`\n", jimp->string);
}

bool jimp_object_begin(Jimp *jimp)
{
    return jimp__get_and_expect_token(jimp, JIMP_OCURLY);
}

bool jimp_object_member(Jimp *jimp)
{
    const char *point = jimp->point;
    if (!jimp__get_token(jimp)) return false;
    if (jimp->token == JIMP_COMMA) {
        if (!jimp__get_and_expect_token(jimp, JIMP_STRING)) return false;
        if (!jimp__get_and_expect_token(jimp, JIMP_COLON)) return false;
        return true;
    }
    if (jimp->token == JIMP_CCURLY) {
        jimp->point = point;
        return false;
    }
    if (!jimp__expect_token(jimp, JIMP_STRING)) return false;
    if (!jimp__get_and_expect_token(jimp, JIMP_COLON)) return false;
    return true;
}

bool jimp_object_end(Jimp *jimp)
{
    return jimp__get_and_expect_token(jimp, JIMP_CCURLY);
}

bool jimp_string(Jimp *jimp)
{
    return jimp__get_and_expect_token(jimp, JIMP_STRING);
}

bool jimp_bool(Jimp *jimp)
{
    jimp__get_token(jimp);
    if (jimp->token == JIMP_TRUE) {
        jimp->boolean = true;
    } else if (jimp->token == JIMP_FALSE) {
        jimp->boolean = false;
    } else {
        jimp_diagf(jimp, "ERROR: expected boolean, but got `%s`\n", jimp__token_kind(jimp->token));
        return false;
    }
    return true;
}

bool jimp_number(Jimp *jimp)
{
    return jimp__get_and_expect_token(jimp, JIMP_NUMBER);
}

bool jimp_is_null_ahead(Jimp *jimp)
{
    const char *point = jimp->point;
    if (!jimp__get_token(jimp)) return false;
    jimp->point = point;
    return jimp->token == JIMP_NULL;
}

bool jimp_is_bool_ahead(Jimp *jimp)
{
    const char *point = jimp->point;
    if (!jimp__get_token(jimp)) return false;
    jimp->point = point;
    return jimp->token == JIMP_TRUE || jimp->token == JIMP_FALSE;
}

bool jimp_is_number_ahead(Jimp *jimp)
{
    const char *point = jimp->point;
    if (!jimp__get_token(jimp)) return false;
    jimp->point = point;
    return jimp->token == JIMP_NUMBER;
}

bool jimp_is_string_ahead(Jimp *jimp)
{
    const char *point = jimp->point;
    if (!jimp__get_token(jimp)) return false;
    jimp->point = point;
    return jimp->token == JIMP_STRING;
}

bool jimp_is_array_ahead(Jimp *jimp)
{
    const char *point = jimp->point;
    if (!jimp__get_token(jimp)) return false;
    jimp->point = point;
    return jimp->token == JIMP_OBRACKET;
}

bool jimp_is_object_ahead(Jimp *jimp)
{
    const char *point = jimp->point;
    if (!jimp__get_token(jimp)) return false;
    jimp->point = point;
    return jimp->token == JIMP_OCURLY;
}

static bool jimp__get_and_expect_token(Jimp *jimp, Jimp_Token token)
{
    if (!jimp__get_token(jimp)) return false;
    return jimp__expect_token(jimp, token);
}

static bool jimp__expect_token(Jimp *jimp, Jimp_Token token)
{
    if (jimp->token != token) {
        jimp_diagf(jimp, "ERROR: expected %s, but got %s\n", jimp__token_kind(token), jimp__token_kind(jimp->token));
        return false;
    }
    return true;
}

#endif // JIMP_IMPLEMENTATION
