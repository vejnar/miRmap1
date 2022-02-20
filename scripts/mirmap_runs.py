#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import itertools
import multiprocessing
import os
import socket
import sys

import mirmap
import mirmap.library_link
import mirmap.empty as shared

def predict_on_mim(args):
    mirna, transcript = args
    mimset = mirmap.mm(transcript[1], mirna[1])
    if shared.libs:
        mimset.libs = shared.libs
    if shared.exe_path:
        mimset.exe_path = shared.exe_path
    mimset.find_potential_targets_with_seed()
    if len(mimset.end_sites) > 0:
        shared.logger.debug(f'Evaluating mirna:{mirna[0]} transcript:{transcript[0]}')
        # De novo features
        mimset.eval_tgs_au()
        mimset.eval_tgs_position()
        mimset.eval_tgs_pairing3p()
        mimset.eval_tgs_score()
        mimset.eval_dg_duplex()
        mimset.eval_dg_open()
        mimset.eval_dg_total()
        mimset.eval_prob_exact()
        mimset.eval_prob_binomial()
        # Rest of the features
        mimset.cons_blss = [0.] * len(mimset.end_sites)
        mimset.selec_phylops = [1.] * len(mimset.end_sites)
        if hasattr(shared, 'aln_path'):
            aln_fname = os.path.join(shared.aln_path, f'{transcript[0]}.fa')
            if os.path.exists(aln_fname):
                if shared.mod_path:
                    mod_fname = os.path.join(shared.mod_path, f'{transcript[0]}.mod')
                    if os.path.exists(mod_fname):
                        print(mod_fname)
                        with open(mod_fname) as modf:
                            mod = modf.read()
                            start = mod.find('TREE: ') + 6
                            end = mod.find(';', start) + 1
                            tree = mod[start:end]
                        mimset.eval_cons_bls(aln_fname=aln_fname, tree=tree, fitting_tree=False)
                        mimset.eval_selec_phylop(aln_fname=aln_fname, mod_fname=mod_fname)
                else:
                    mimset.eval_cons_bls(aln_fname=aln_fname, tree='species.tree', fitting_tree=True)
                    mimset.eval_selec_phylop(aln_fname=aln_fname, mod_fname=mod_fname)
        mimset.eval_score()
        if shared.combine:
            return mirna[0], transcript[0], mimset.end_sites, mimset.seed_lengths, mimset.nb_mismatches_except_gu_wobbles, mimset.nb_gu_wobbles, mimset.tgs_au, mimset.tgs_position, mimset.tgs_pairing3p, mimset.tgs_score, mimset.dg_duplex, mimset.dg_binding, mimset.dg_duplex_seed, mimset.dg_binding_seed, mimset.dg_open, mimset.dg_total, mimset.prob_exact, mimset.prob_binomial, mimset.cons_bls, mimset.selec_phylop, mimset.score
        else:
            return mirna[0], transcript[0], mimset.end_sites, mimset.seed_lengths, mimset.nb_mismatches_except_gu_wobbles, mimset.nb_gu_wobbles, mimset.tgs_aus, mimset.tgs_positions, mimset.tgs_pairing3ps, mimset.tgs_scores, mimset.dg_duplexs, mimset.dg_bindings, mimset.dg_duplex_seeds, mimset.dg_binding_seeds, mimset.dg_opens, mimset.dg_totals, mimset.prob_exacts, mimset.prob_binomials, mimset.cons_blss, mimset.selec_phylops, mimset.scores

def format_number(v):
    if isinstance(v, int):
        return str(v)
    else:
        s1 = str(v)
        s2 = f'{v:.8}'
        if len(s1) < len(s2):
            return s1
        else:
            return s2

def main(argv=None):
    # Parameters
    if argv is None:
        argv = sys.argv
    parser = argparse.ArgumentParser(description='Predict miRNA targets.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-m', '--mirna', dest='mirna_seqs', action='append', help='miRNA sequence')
    parser.add_argument('-n', '--mirna-id', dest='mirna_ids', action='append', help='miRNA IDs')
    group.add_argument('-a', '--mirna-fasta', dest='mirna_fname_fasta', action='store', help='miRNA Fasta file')
    group.add_argument('-b', '--mirna-tab', dest='mirna_fname_tab', action='store', help='miRNA tabulated file')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-t', '--transcript', dest='transcript_seqs', action='append', help='Transcript sequence')
    parser.add_argument('-i', '--transcript-id', dest='transcript_ids', action='append', help='Transcript IDs')
    group.add_argument('-f', '--transcript-fasta', dest='transcript_fname_fasta', action='store', help='Transcript Fasta file')
    group.add_argument('-u', '--transcript-tab', dest='transcript_fname_tab', action='store', help='Transcript tabulated file')
    parser.add_argument('-z', '--site-id', dest='site_id', action='store_true', help='Add a column with site IDs')
    parser.add_argument('-c', '--combine', dest='combine', action='store_true', help='Combine multiple targets (miRNA-mRNA 1 to 1 relationships)')
    parser.add_argument('-l', '--library', dest='library_path', action='store', help='External C libraries path')
    parser.add_argument('-e', '--exe', dest='exe_path', action='store', help='External programs path')
    parser.add_argument('-s', '--aln', dest='aln_path', action='store', help='Multiple sequences alignment(s) path')
    parser.add_argument('-d', '--mod', dest='mod_path', action='store', help='Model(s) path')
    parser.add_argument('-o', '--output', dest='output_fname', action='store', default='-', help='Worker(s)')
    parser.add_argument('-w', '--workers', dest='num_worker', action='store', type=int, default=1, help='Worker(s)')
    parser.add_argument('-g', '--logging-level', dest='logging_level', action='store', default='debug', help='Logging level')
    args = parser.parse_args(argv[1:])

    # Logging
    try:
        import cevbio.mylog as mylog
        logger = mylog.define_root_logger('mirmap', level=args.logging_level)
    except ImportError:
        import logging as logger
    shared.logger = logger
    logger.debug(f'Starting on {socket.gethostname()}')

    # Paths
    if args.aln_path:
        shared.aln_path = args.aln_path
    if args.mod_path:
        shared.mod_path = args.mod_path

    # Prediction defaults
    try:
        if not os.getcwd() in sys.path:
            sys.path.insert(1, os.getcwd())
        import mirmap_defaults
        logger.debug('Prediction defaults changed')
    except ImportError:
        logger.debug('Prediction defaults kept')

    # Combining targets
    shared.combine = args.combine

    # Loading external C libraries
    if args.library_path:
        shared.libs = mirmap.library_link.LibraryLink(args.library_path)
    else:
        shared.libs = None

    # Adding external programs path
    if args.exe_path:
        shared.exe_path = args.exe_path
    else:
        shared.exe_path = None

    # Reading sequences
    if args.mirna_fname_fasta:
        mirnas = mirmap.utils.load_fasta(args.mirna_fname_fasta)
        if args.mirna_ids:
            for mid in mirnas.keys():
                if mid not in args.mirna_ids:
                    del mirnas[mid]
    elif args.mirna_fname_tab:
        with open(args.mirna_fname_tab) as f:
            mirnas = dict([l.rstrip().split('\t') for l in f])
    else:
        if args.mirna_ids:
            mirnas = {}
            for i in range(len(args.mirna_ids)):
                mirnas[args.mirna_ids[i]] = args.mirna_seqs[i]
        else:
            mirnas = dict(zip(range(1, len(args.mirna_seqs)+1), args.mirna_seqs))
    if args.transcript_fname_fasta:
        transcripts = mirmap.utils.load_fasta(args.transcript_fname_fasta)
        if args.transcript_ids:
            for tid in transcripts.keys():
                if tid not in args.transcript_ids:
                    del transcripts[tid]
    elif args.transcript_fname_tab:
        with open(args.transcript_fname_tab) as f:
            transcripts = dict([l.rstrip().split('\t') for l in f])
    else:
        if args.transcript_ids:
            transcripts = {}
            for i in range(len(args.transcript_ids)):
                transcripts[args.transcript_ids[i]] = args.transcript_seqs[i]
        else:
            transcripts = dict(zip(range(1, len(args.transcript_seqs)+1), args.transcript_seqs))
    logger.info(f'Starting predictions with {len(mirnas)} miRNA(s) and {len(transcripts)} transcript(s)')

    # Predictions
    if args.num_worker > 1:
        pool = multiprocessing.Pool(args.num_worker)
        tsp_results = pool.map_async(predict_on_mim, itertools.product(mirnas.items(), transcripts.items()), chunksize=5).get(1e+10)
        pool.close()
    else:
        tsp_results = map(predict_on_mim, itertools.product(mirnas.items(), transcripts.items()))

    # Output
    if args.output_fname == '-':
        outf = sys.stdout
    else:
        outf = open(args.output_fname, 'w')
    for mim in tsp_results:
        if mim is not None:
            if args.combine:
                outf.write('\t'.join([str(mim[0]), str(mim[1]), ','.join(map(str, mim[2])), ','.join(map(str, mim[3])), ','.join(map(str, mim[4])), ','.join(map(str, mim[5]))] + list(map(str, mim[6:]))) + '\n')
            else:
                for isite, site in enumerate(zip(*mim[2:])):
                    fields = [str(mim[0]), str(mim[1])]
                    if args.site_id:
                        fields.append(str(isite+1))
                    fields.extend([format_number(v) for v in site])
                    outf.write('\t'.join(fields) + '\n')
    outf.close()

    # End
    if len(mirnas) == 1:
        logger.info(f'Predictions ready for miRNA {list(mirnas.keys())[0]}')
    else:
        logger.info('Predictions ready')

if __name__ == '__main__':
    sys.exit(main())
