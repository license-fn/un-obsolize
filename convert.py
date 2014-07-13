import argparse
import os
import re
import shutil
import sys

class UnObsolizer:

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

        Keyword arguments:
        only_current_dir -- do not recurse into all other directories
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
        parser.Namespace -- contains values for 'recurse', 'directory',
        and 'file' options
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
        for f in self.files:
            parser = FileParser(f)

class FileParser:

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

    def __init__(self, file_name):
        self.file_name = file_name
        self.current_state = FileParser.SEARCH_FOR_FUNC
        self.accumulated_lines = []
        self.function_decl = ''
        self.function_args = []
        self.function_ret_type = ''
        self.previous_line = ''
        self.num_function_args = 0

        # Save original file in case of disaster
        shutil.copyfile(file_name, file_name + '.bak')
        self.output_file = open(self.file_name, 'w+')

        # This is pass #0
        self.operate_on_file(self.function_converter)

        print('init:', file_name)

    def operate_on_file(self, handle):
        file_ = open(self.file_name + '.bak', 'r')
        for line in file_:
            handle(line)
            self.previous_line = line

    def function_converter(self, line):

        if self.current_state is FileParser.SEARCH_FOR_FUNC:
            self.search_for_func(line)
        elif self.current_state is FileParser.READ_ARGUMENTS:
            self.read_arguments(line)
        elif self.current_state is FileParser.REPLACE_FUNCTION:
            self.replace_function(line)

    def search_for_func(self, line):


        func_name_match = re.search(self.function_name_re, line)
        if func_name_match:
            print('found an old function delcaration')
            print("\tname:", func_name_match.group('name'))
            print("\targuments:", func_name_match.group('args'))
            print("checking previous line for return value")
            if func_name_match.group('args'):
                self.num_function_args = len(
                    func_name_match.group('args').split(','))
            print('num args: ', self.num_function_args)
            ret_value_match = re.search(
                self.return_value_re, self.previous_line)
            if ret_value_match:
                self.accumulated_lines.append(self.previous_line)
                print('found return value: ')
                print('\tstatic: ', ret_value_match.group('static'))
                print('\tret_val: ', ret_value_match.group('retval'))
                print('\tpointer: ', ret_value_match.group('pointer'))
                if ret_value_match.group('static'):
                    self.function_decl += 'static '
                self.function_decl += ret_value_match.group('retval') + ' '
                if ret_value_match.group('pointer'):
                    self.function_decl += '*'
            else:
                self.function_decl = 'void '
                print('no return value found... defaulting to void')
                self.output_file.write('void\n')

            self.function_decl = func_name_match.group('name')

            print('function delc: ', self.function_decl)
            print('--------------------')
            if self.num_function_args is 0:
                self.current_state = FileParser.REPLACE_FUNCTION
            else:
                self.current_state = FileParser.READ_ARGUMENTS
        else:
             self.output_file.write(line)
             self.reset_state()



    def read_arguments(self, line):

        arg_match = re.search(self.function_arg_re, line)
        if arg_match:
            arg_type = arg_match.group('type')
            arg_name = arg_match.group('name')
            arg_ptr = True if arg_match.group('pointer') else False
            self.function_args.append((arg_type, arg_name, arg_ptr))

        if len(self.function_args) is self.num_function_args:
            print('found all arguments')
            print("found arg: ", self.function_args)
            self.current_state = FileParser.REPLACE_FUNCTION

    def replace_function(self, line):

        open_curley_match = re.search(self.function_begin_re, line)
        if open_curley_match:
#            import pdb; pdb.set_trace()

            print('time to replace function', self.accumulated_lines)
            self.function_decl += '('

            index = 1
            for arg in self.function_args:
                self.function_decl += arg[0]
                self.function_decl += '* ' if arg[2] else ' '
                self.function_decl += arg[1]
                if index < len(self.function_args):
                    self.function_decl += ', '
                index += 1

            self.function_decl += ')\n'
            print('with:', self.function_decl)
            self.output_file.write(self.function_decl)
            self.output_file.write(line)

        self.reset_state()

    def print_accumulated_lines(self):
        self.output_file.writelines(self.accumulated_lines)

    def reset_state(self):
        self.current_state = FileParser.SEARCH_FOR_FUNC
        self.accumulated_lines = []
        self.function_decl = ''
        self.function_args = []
        self.function_ret_type = ''
        self.num_function_args = 0


if __name__ == '__main__':
    unob = UnObsolizer()
    unob.get_files_from_args()
    print('files to visit:', unob.files)
    unob.parse_files()
