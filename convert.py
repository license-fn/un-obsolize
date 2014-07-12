import argparse
import re
import sys
import os
from os import walk

class UnObsolizer:

    def __init__(self):
        self.files = []
        self.get_files()


    def get_files(self):
        """
        Sets self.files to the list of files that will be operated on, based on
        the arguments given on the command line.
        """
        args = self.parse_arguments()
        self.files.extend([os.path.join(os.getcwd(), f) for f in args.files])

        if args.recurse or args.directory:
            self.append_directory_files(
                only_current_dir=(args.directory and not args.recurse))

        # Filter files to ensure *.c
        c_file_regex = re.compile(r'\S+\.c$')
        self.files = [ f for f in self.files if (re.search(c_file_regex, f)) ]

        print("files to visit:", self.files)

    def append_directory_files(self, only_current_dir):
        """ 
        Walk through directories and record the files we need to visit if the
        user specified recursive or directory mode. Appends all found files
        to 'self.files'.

        Keyword arguments:
        only_current_dir -- do not recurse into all other directories
        """
        for (dirpath, dirnames, filenames) in walk(os.getcwd()):
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


if __name__ == '__main__':
    unob = UnObsolizer()
