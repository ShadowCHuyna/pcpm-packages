[original repo](https://github.com/raysan5/raylib)

The `raylib-module` package is an attempt to make something like "modules."
If you try to link in a project two libraries that have at least one function with the same name (or you already have one), you get a linker error. Surprise.

Instead:
- `RaylibModule` - a structure with pointers to all functions.
- `import_RaylibModule` - loads the `dll/so` and fills the structure.
- In code, you work through `rl->FunctionName`.

There are no symbol conflicts because nothing is linked directly. Functions are loaded at runtime and stored in the pointer structure, not in the final binary’s symbol table.
Downside: macros tied to functions break. But they can be rewritten to use pointers.

Uses the library: [raysan5/raylib](https://github.com/raysan5/raylib)
```c
#include "raylib-module.h"
RaylibModule* rl;

int main(void){
    rl = import_RaylibModule("./libraylib.so.5.5.0");

    rl->InitWindow(800, 450, "raylib [core] example - basic window");
    while (!rl->WindowShouldClose())
    {
        rl->BeginDrawing();
            rl->ClearBackground(RAYWHITE);
            rl->DrawText("Congrats! You created your first window!", 190, 200, 20, LIGHTGRAY);
        rl->EndDrawing();
    }
    rl->CloseWindow();

    return 0;
}
```