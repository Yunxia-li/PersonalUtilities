#!/usr/bin/env python
import os
import time
import sys
import re
from optparse import OptionParser


def require_options(print_title):
    usage = "python this_script.py a_list_of_fasta_files -o output.fasta"
    parser = OptionParser(usage=usage)
    parser.add_option('-o', dest='output',
                      help='output file fasta file')
    parser.add_option('--separate', dest='aligned', default=True, action='store_false',
                      help='By default the input fasta is treated as alignment. Choose to treat as separate sequences.')
    parser.add_option('--sort', dest='sort_file_name', default=False, action='store_true',
                      help='By default this script would concatenate the file by the original argument order, '
                           'which may sometimes cause disorder when using wildcard (*). Choose to reorder the '
                           'concatenate order by file names.')
    parser.add_option('--config', dest='configuration_file',
                      help='If chosen and the input are aligned, output a configuration file recording the locations.')
    parser.add_option('--prefix', dest="configure_prefix", default="DNA, ",
                      help="For typical RAxML partition format, it needs assignment for model. (Default: DNA, )")
    parser.add_option("--quiet", dest="quiet", default=False, action="store_true")
    options, args = parser.parse_args()
    if not (options.output and args):
        parser.print_help()
        sys.stderr.write('\n######################################\nERROR: Insufficient REQUIRED arguments!\n\n')
        exit()
    if not options.quiet:
        sys.stdout.write(print_title + "\n")
    if options.sort_file_name:
        min_len = min([len(file_name) for file_name in args])
        go_to = 0
        while go_to < min_len:
            this_character = args[0][go_to]
            is_equal = True
            for go_file in range(1, len(args)):
                if args[go_file][go_to] != this_character:
                    is_equal = False
            if not is_equal:
                break
            go_to += 1
        go_back = 1
        while go_back <= min_len:
            this_character = args[0][-go_back]
            is_equal = True
            for go_file in range(1, len(args)):
                if args[go_file][-go_back] != this_character:
                    is_equal = False
            if not is_equal:
                break
            go_back += 1
        try:
            args.sort(key=lambda x: int(x[go_to: len(x)-go_back+1]))
        except ValueError:
            args.sort()
        sys_args = sys.argv
        count_argv = 0
        sorted_argvs = set(args)
        while count_argv < len(sys_args):
            if sys_args[count_argv] in sorted_argvs:
                del sys_args[count_argv]
            else:
                count_argv += 1
        if not options.quiet:
            sys.stdout.write(' '.join(sys_args)+' '+' '.join(args) + '\n\n')
    else:
        if not options.quiet:
            sys.stdout.write(' '.join(sys.argv) + '\n\n')
    return options, args


def read_fasta(fasta_file):
    fasta_handler = open(fasta_file)
    names = []
    seqs = []
    this_line = fasta_handler.readline()
    interleaved = 0
    while this_line:
        if this_line.startswith('>'):
            names.append(this_line[1:].strip())
            this_seq = ''
            this_line = fasta_handler.readline()
            seq_line_count = 0
            while this_line and not this_line.startswith('>'):
                if seq_line_count == 1:
                    interleaved = len(this_seq)
                this_seq += this_line.strip()
                this_line = fasta_handler.readline()
                seq_line_count += 1
            seqs.append(this_seq.replace(" ", ""))
        else:
            this_line = fasta_handler.readline()
    fasta_handler.close()
    return [names, seqs, interleaved]


def write_fasta(out_file, matrix, overwrite):
    if not overwrite:
        while os.path.exists(out_file):
            out_file = '.'.join(out_file.split('.')[:-1]) + '_.' + out_file.split('.')[-1]
    out_handler = open(out_file, 'w')
    if matrix[2]:
        for i in range(len(matrix[0])):
            out_handler.write('>'+matrix[0][i]+'\n')
            j = matrix[2]
            while j < len(matrix[1][i]):
                out_handler.write(matrix[1][i][(j-matrix[2]):j]+'\n')
                j += matrix[2]
            out_handler.write(matrix[1][i][(j-matrix[2]):j]+'\n')
    else:
        for i in range(len(matrix[0])):
            out_handler.write('>'+matrix[0][i] + '\n')
            out_handler.write(matrix[1][i] + '\n')
    out_handler.close()


def main():
    time0 = time.time()
    print_title = ""
    options, args = require_options(print_title)
    fasta_matrices = []
    seq_names_list = []
    seq_names_set = set()
    matrix_names = []
    if options.aligned:
        matrix_lengths = []

    for fasta_file in args:
        this_matrix = read_fasta(fasta_file)

        here_lengths = [len(here_seq) for here_seq in this_matrix[1]]
        lengths_set = set(here_lengths)
        if this_matrix[1] and lengths_set != {0}:
            if options.aligned:
                matrix_lengths.append(here_lengths[0])
                if len(lengths_set) != 1:
                    for i in range(1, len(here_lengths)):
                        if here_lengths[i] != matrix_lengths[-1]:
                            sys.stderr.write("Error: Unequal length between " + this_matrix[0][0] + " and "
                                             + this_matrix[0][i] + " in "+fasta_file+"!\n")
                            exit()

            fasta_matrices.append(this_matrix)
            matrix_names.append(re.sub(".fasta$", '', os.path.basename(fasta_file)))
            for seq_name in this_matrix[0]:
                if seq_name not in seq_names_set:
                    seq_names_list.append(seq_name)
                    seq_names_set.add(seq_name)
        else:
            sys.stdout.write("Warning: no bases found in " + fasta_file + ", skipping this file!\n")

    out_dict = {in_seq_name: '' for in_seq_name in seq_names_list}
    if options.aligned:
        if options.configuration_file:
            config_file = open(options.configuration_file, 'w')
            go_base = 0
        for i in range(len(fasta_matrices)):
            for j in range(len(fasta_matrices[i][0])):
                this_seq_name = fasta_matrices[i][0][j]
                out_dict[this_seq_name] += fasta_matrices[i][1][j]
                seq_names_set.remove(this_seq_name)
            for add_seq_name in seq_names_set:
                out_dict[add_seq_name] += "-"*matrix_lengths[i]
            if options.configuration_file:
                config_file.write(options.configure_prefix + matrix_names[i]+
                                  ' = ' + str(go_base + 1) + '-' + str(go_base + matrix_lengths[i]) + '\n')
                go_base += matrix_lengths[i]
            seq_names_set = set(seq_names_list)
    else:
        for this_matrix in fasta_matrices:
            for i in range(len(this_matrix[0])):
                out_dict[this_matrix[0][i]] += this_matrix[1][i]
    out_matrix = [seq_names_list, [out_dict[this_name] for this_name in seq_names_list], fasta_matrices[0][2]]
    write_fasta(options.output, out_matrix, False)
    if not options.quiet:
        sys.stdout.write("Cost: " + str(time.time()-time0) + "\n")


if __name__ == '__main__':
    main()
