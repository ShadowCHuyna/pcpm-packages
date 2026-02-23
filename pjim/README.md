The `pjim` package generates 2 functions of the form
`pjim_<struct name>_<serialization/deserialization>`
for structures marked with `// @PJIM`.

Uses the library [tsoding/jim](https://github.com/tsoding/jim).
```c
#include <stdio.h>
#include "jim.h"
#include "jimp.h"
#include "pjim.h"

// @PJIM
typedef struct
{
    int number;
    int number_arr_capacity;
    int number_arr[10];
} some_struct;


int main(void){
    Jim jim = {.pp=4};
    some_struct ss = {.number=33, .number_arr_capacity=3};
    for (size_t i = 0; i < ss.number_arr_capacity; i++)
        ss.number_arr[i] = i;
    
    // serialization
    pjim_some_struct_serialization(&jim, &ss); // auto-generated function
    printf("serialized structure JSON:\n");
    fwrite(jim.sink, jim.sink_count, 1, stdout);

    // deserialization
    printf("\ndeserialized structure:\n");
    some_struct ds = {0};
    Jimp jimp = {0};
    jimp_begin(&jimp, "", jim.sink, jim.sink_count); 
    pjim_some_struct_deserialization(&jimp, &ds); // auto-generated function

    printf("{\n\t\"number\": %d,\n\t\"number_arr_capacity\": %d,\n\t\"number_arr\": [\n", ds.number, ds.number_arr_capacity);
    for (size_t i = 0; i < ds.number_arr_capacity; i++)
        printf("\t\t%d,\n", ds.number_arr[i]);
    printf("\t]\n}\n");
    return 0;
}
```
`./build/bin/main`:
```json
serialized structure JSON:
{
    "number": 33,
    "number_arr_capacity": 3,
    "number_arr": [
        0,
        1,
        2
    ]
}
deserialized structure:
{
    "number": 33,
    "number_arr_capacity": 3,
    "number_arr": [
        0,
        1,
        2,
    ]
}
```

So you just mark the structure, and the package generates the serialization/deserialization functions automatically.
