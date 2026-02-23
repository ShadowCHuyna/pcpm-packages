#ifndef PLL_H_
#define PLL_H_


typedef struct {
    const char* path;   // путь к библиотеке
    void* handle;       // dlopen() / HMODULE
} Lib;

/*
Lib lib = {.path="path/to/lib.so"};
void* var = pll_get(&lib, "var");
*/
void* pll_get(Lib* lib, const char* name);
void* pll_close_lib(Lib* lib);

#endif

#ifdef PLL_IMPLEMENTATION

#ifdef _WIN32
    #include <windows.h>
#else
    #include <dlfcn.h>
#endif
#include <stdio.h>

void* pll_get(Lib* lib, const char* name)
{
    if (!lib || !name)
        return NULL;

    /* Открываем библиотеку при первом обращении */
    if (!lib->handle)
    {
#ifdef _WIN32
        HMODULE h = LoadLibraryA(lib->path);
        if (!h)
            return NULL;
        lib->handle = (void*)h;
#else
        void* h = dlopen(lib->path, RTLD_NOW | RTLD_LOCAL);
        if (!h)
            return NULL;
        lib->handle = h;
#endif
    }

#ifdef _WIN32
    return (void*)GetProcAddress((HMODULE)lib->handle, name);
#else
    return dlsym(lib->handle, name);
#endif
}


void* pll_close_lib(Lib* lib)
{
    if (!lib || !lib->handle)
        return NULL;

#ifdef _WIN32
    FreeLibrary((HMODULE)lib->handle);
#else
    dlclose(lib->handle);
#endif

    lib->handle = NULL;
    return NULL;
}
#endif