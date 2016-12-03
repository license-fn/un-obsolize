# un-obsolize

A Python script to assist in removing obsolete (K&R) forward declarations and function definitions in C code. The K&R syntax is replaced with ANSI syntax.

Forward declarations and function defininitions can be located in separate files and conversion will still work, provided that the script is invoked on all relavant files.

Files are backed up before any changes are made. Backed up files are named `{filename}.bak`.

### A Note on Functionality
I wrote this script to help automate some mindless tasks for work. It is not intended to be a full-blown solution that handles every single odd conversion case. This script served its purpose for the specific code base that I was converting, but your milelage may vary.

This script is extremely limited. It is not a C parser. Function declarations must have the exact same format as shown in the conversion sample below in order for them to be detected. (Yes, the return value must be on a different line than the function name.) Even then, this script may have false positives and false negatives. For this reason, the script will, by default, prompt for confirmation before making any changes. Files are always backed up before any changes are made.

# Conversion Sample
This script will convert in the following way:

Obsolete K&R syntax:
```C
// Obsolete forward declaration
int foo();

// Obsolete function implementation
int            // This return value must be on a separate line in order for it to be detected
foo(a, b, c)
  int a;
  void *b;
  char c;
{
  // Stuff
}
```

Converted ANSI syntax:
```C
// ANSI forward declaration
int foo(int a, void *b, char c)

// ANSI function implementation
int foo(int a, void *b, char c)
{
  // Stuff
}
```

# Requirements
Python >= 3.2

# Usage
This script is intended to be run from the shell:

```bash
python3 convert.py
```
### Arguments
```
usage: convert.py [-h] [-r] [-d] [-xc] [--ext NEW_EXT] [--re INPUT_RE] [-gm]
                  [file [file ...]]

Convert some C code.

positional arguments:
  file           Files to operate on. Optional if [-r/-d] is applied

optional arguments:
  -h, --help     show this help message and exit
  -r             Recurse and operate on all files in the current and sub-
                 directories (implies -d)
  -d             Operate on all files in the current directory
  -xc            Do not prompt for confirmation before making a change.
  --ext NEW_EXT  Specify a new file extension to change the converted files
                 to. Useful when converting from *.c to *.cpp. Example: [--ext
                 cpp]
  --re INPUT_RE  Specify a Python regex to filter the files that are found
                 with [-d/-r]. Default is `\S+\.c$`, which will usually match
                 *.c files.
  -gm            Only valid with [--ext]. When changing file extensions,
                 perform a Git move. Useful when operating in a Git
                 repository.
```
