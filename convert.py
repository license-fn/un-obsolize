import argparse
import os
import re
import shutil
import sys

class UnObsolizer:
    """
    Creates a list of files to parse based on command line arguments.

    This class is not required to have parsing done, it simply compiles a list
    of files to operate on, and then creates a ``FileParser`` for each
    file.

    Usage:
      unob = UnObsolizer()
      unob.get_files_from_args()
      unob.parse_files()
    """

    def __init__(self):
        self.files = []

    def get_files_from_args(self):
        """
        Sets self.files to the list of files that will be operated on, based on
        the arguments given on the command line.
        """
        args = self.parse_arguments()
        self.files.extend([os.path.join(os.getcwd(), f) for f in args.files])

        if args.recurse or args.directory:
            self.append_directory_files(
                only_current_dir=(not args.recurse))

        # Filter files to ensure *.c
        c_file_regex = re.compile(r'\S+\.c$')
        self.files = [ f for f in self.files if (re.search(c_file_regex, f)) ]

    def append_directory_files(self, only_current_dir):
        """ 
        Walk through directories and record the files we need to visit if the
        user specified recursive or directory mode. Appends all found files
        to 'self.files'.

        Args:
        only_current_dir (bool): do not recurse into all other directories
        """
        for (dirpath, dirnames, filenames) in os.walk(os.getcwd()):
            for f in filenames:
                self.files.append(os.path.join(dirpath, f))
            if only_current_dir:
                break;

    def parse_arguments(self):
        """
        Handle parsing arguments from the command line

        Returns:
        parser.Namespace: contains values for 'recurse', 'directory', and 'file'
          options
        """
        parser = argparse.ArgumentParser(description="Convert some C code.")
        parser.add_argument(
            '-r', dest='recurse', action='store_const', const=True,
            default=False,
            help='recurse and operate on sub-directories (implies -d)')
        parser.add_argument(
            '-d', dest='directory', action='store_const', const=True,
            default=False, help='operate on the current directory')
        parser.add_argument(
            'files', metavar='file', nargs='*',
            help='Files to operate on. Optional if [-r/-d] is applied')

        return parser.parse_args()

    def parse_files(self):
        """
        Triggers the parsing process for all files in the list 'self.files'.
        Useful if you wish to add files manually before starting the process.
        """
        for f in self.files:
            parser = FileParser(f)

class FileParser:

    # Parser states
    SEARCH_FOR_FUNC = 1
    READ_ARGUMENTS = 2
    REPLACE_FUNCTION = 3

    return_value_re = re.compile(
        r'^\s*(?P<static>static)?\s*(?P<retval>[a-zA-Z_][a-zA-Z0-9_]*)\s*'
        r'(?P<pointer>\*)?\s*$')
    function_name_re = re.compile(
        r'^\s*(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*'
        r'\(\s*(?P<args>[a-zA-Z_][a-zA-Z0-9_]*'
        r'(\s*,\s*[a-zA-Z_][a-zA-Z0-9_]*)*)?\s*\)\s*$')
    function_arg_re = re.compile(
        r'^\s*(?P<type>[a-zA-Z_][a-zA-Z0-9_]*)\s*(?P<pointer>\*)?\s*'
        r'(?P<name>\S+)\s*;\s*$')
    function_begin_re = re.compile(r'\s*\{\s*$')

    forward_declaration_re = re.compile(
        r'^\s*(?P<type>[a-zA-Z_][a-zA-Z0-9_]*)?\s*\*?\s*'
        '(?P<name>[a-zA-Z_][a-zA-Z0-9_]*)\s*\(\s*\)\s*;\s*$')

    def __init__(self, file_name):
        """
        Initializes and tells the parser to operate on 'file_name'.
        No action is required other than initializing this class; the parsing
        process is automatically initiated.
        A backup file is saved in 'file_name.bak'; just in-case the program
        explodes.

        Args:
        file_name (string): the file to operate on
        """
        self.current_state = FileParser.SEARCH_FOR_FUNC
        self.function_name = ''
        self.function_args = []
        self.previous_line = ''
        self.function_args_count = 0
        self.function_dict = {}

        # Save original file in case of disaster
        backup_file = file_name + '.bak'
        shutil.copyfile(file_name, backup_file)
        self.output_file = open(file_name, 'w+')
        self.input_file = open(backup_file, 'r')

        # This is pass #0
        self.operate_on_file(backup_file, self.function_converter)
        print('function_dict:', self.function_dict)

        # This is pass #2 (needs to operate on output file)
        self.operate_on_file(backup_file, self.declaration_converter)

    def declaration_converter(self, line):
        forward_decl_match = re.search(self.forward_declaration_re, line)
        if forward_decl_match:
            new_forward_decl_args = ''
            func_name = forward_decl_match.group('name')
            args_tuple_list = self.function_dict[func_name]
            index = 1
            for arg_tuple in args_tuple_list:
                new_forward_decl_args += arg_tuple[0]
                if arg_tuple[2]:
                    new_forward_decl_args += '* '
                else:
                    new_forward_decl_args += ' '
                new_forward_decl_args += arg_tuple[1]
                if index < len(args_tuple_list):
                    new_forward_decl_args += ', '
                index += 1


            print("forwrad decl match:", func_name)
            print('\t takes args:', self.function_dict[func_name])
            repl = re.sub('\((.*)\)', '(' + new_forward_decl_args + ')', line)
            print('\t replace w/:', repl)
        else:
            pass
            # output line

    def operate_on_file(self, file_name, handle):
        """
        Calls the passed in function on every line of the specified file.
        There will be two passes on the file, so this is useful to avoid
        redundant code.

        Args:
        file_name (string): name of the file to read
        handle (function(string)): the function to call for every line of the
          file (takes the line of the file as an argument)
        """
        file_ = open(file_name, 'r')
        for line in file_:
            handle(line)
            self.previous_line = line

    def function_converter(self, line):
        """
        The main state handler for the function-converter.
        Passes 'line' onto the proper function depending on the current state.

        Args:
        line (string): the current string to be processing
        """
        if self.current_state is FileParser.SEARCH_FOR_FUNC:
            self.search_for_func(line)
        elif self.current_state is FileParser.READ_ARGUMENTS:
            self.read_arguments(line)
        elif self.current_state is FileParser.REPLACE_FUNCTION:
            self.replace_function(line)

    def search_for_func(self, line):
        """
        Searches 'line' for a function declaration of the form:
        '[name]([arg], [arg])'.

        Args:
        line (string): the string to search for a function in

        Modified instance variables:
        function_decl: will contain the name of the function (if one is found)
        current_state: set to the proper next state based on the # of
          arguments expected
        function_args_count: set to the expected number of arguments
        """
        func_name_match = re.search(self.function_name_re, line)
        if func_name_match:
            # Grab expected number of arguments
            if func_name_match.group('args'):
                self.function_args_count = len(
                    func_name_match.group('args').split(','))

            # Use 'void' if there is no return value
            ret_value_match = re.search(self.return_value_re,
                                        self.previous_line)
            if not ret_value_match:
                self.output_file.write('int\n')
            self.function_name = func_name_match.group('name')
            if self.function_args_count is 0:
                self.current_state = FileParser.REPLACE_FUNCTION
            else:
                self.current_state = FileParser.READ_ARGUMENTS
        else:
             self.output_file.write(line)
             self.reset_state()

    def read_arguments(self, line):
        """
        Reads the arguments that follow the function declaration. Stores
        them in a tuple for re-writing later.

        Args:
        line (string): the string to search for an argument in

        Modified instance variables:
        function_args: add found argument tuples to the list
        current_state: set to next state when all arguments have been found
        """
        arg_match = re.search(self.function_arg_re, line)
        if arg_match:
            arg_type = arg_match.group('type')
            arg_name = arg_match.group('name')
            arg_ptr = True if arg_match.group('pointer') else False
            self.function_args.append((arg_type, arg_name, arg_ptr))
        if len(self.function_args) is self.function_args_count:
            self.current_state = FileParser.REPLACE_FUNCTION

    def replace_function(self, line):
        """
        Replaces the obsolete function header with the new one built from
        the function name and the argument tuples. Then resets the state
        machine.

        Args:
        line (string): the line containing the opening brace of the function
        """
        open_curley_match = re.search(self.function_begin_re, line)
        if open_curley_match:
            function_declaration = self.function_name
            function_declaration += '('
            index = 1
            for arg in self.function_args:
                function_declaration += arg[0]
                function_declaration += '* ' if arg[2] else ' '
                function_declaration += arg[1]
                if index < len(self.function_args):
                    function_declaration += ', '
                index += 1
            function_declaration += ')\n'
            self.output_file.write(function_declaration)
            self.output_file.write(line)
            self.function_dict[self.function_name] = self.function_args

        self.reset_state()

    def reset_state(self):
        """
        Resets the state machine to its default values.
        """
        self.current_state = FileParser.SEARCH_FOR_FUNC
        self.accumulated_lines = []
        self.function_name = ''
        self.function_args = []
        self.function_ret_type = ''
        self.function_args_count = 0


if __name__ == '__main__':
    unob = UnObsolizer()
    unob.get_files_from_args()
    unob.parse_files()
