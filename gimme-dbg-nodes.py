#! /usr/bin/env python3
"""
"""
from __future__ import print_function
import argparse
from sourmash_lib import MinHash
from spacegraphcats import graph_parser
from spacegraphcats.catlas_reader import CAtlasReader
from spacegraphcats.catlas import CAtlas
from spacegraphcats.graph import VertexDict
from collections import defaultdict
import os
import sys

KSIZE=31

def load_orig_sizes_and_labels(original_graph_filename):
    "Load the sizes & labels for the original DBG node IDs"
    orig_to_labels = defaultdict(list)
    orig_sizes = defaultdict(int)
    def parse_source_graph_labels(node_id, size, names, vals):
        assert names[0] == 'labels'
        labels = vals[0]
        orig_sizes[node_id] = size
        if labels:
            orig_to_labels[node_id] = list(map(int, labels.strip().split(' ')))

    def nop(*x):
        pass

    with open(original_graph_filename) as fp:
        graph_parser.parse(fp, parse_source_graph_labels, nop)

    return orig_sizes, orig_to_labels


def load_dom_to_orig(assignment_vxt_file):
    "Load the mapping between level0/dom nodes and the original DBG nodes."
    dom_to_orig = defaultdict(list)
    for line in open(assignment_vxt_file, 'rt'):
        orig_node, dom_list = line.strip().split(',')
        orig_node = int(orig_node)
        dom_list = list(map(int, dom_list.split(' ')))

        for dom_node in dom_list:
            dom_to_orig[dom_node].append(orig_node)

    return dom_to_orig

def load_mh_dump(mh_filename):
    "Load a MinHash from a file created with 'sourmash dump'."
    with open(mh_filename) as fp:
        hashes = fp.read().strip().split(' ')
    query_mh = MinHash(len(hashes), KSIZE)

    for h in hashes:
        query_mh.add_hash(int(h))
    return query_mh


def main():
    p = argparse.ArgumentParser()
    p.add_argument('catlas_prefix', help='catlas prefix')
    p.add_argument('catlas_r', type=int, help='catlas radius to load')
    p.add_argument('mh_file', help='file containing dumped MinHash signature')
    p.add_argument('--strategy', type=str, default='bestnode',
                   help='search strategy: bestnode, xxx')
    p.add_argument('--searchlevel', type=int, default=0)
    p.add_argument('-q', '--quiet', action='store_true')
    p.add_argument('--append-csv', type=str,
                   help='append results in CSV to this file')
    p.add_argument('-o', '--output', metavar="filename",
                   type=argparse.FileType('w'),
                   default=None, dest='output_fp')
    args = p.parse_args()

    ### first, parse the catlas gxt
    catlas = CAtlasReader(args.catlas_prefix, args.catlas_r)

    _radius = args.catlas_r
    _basename = os.path.basename(args.catlas_prefix)
    _catgxt = '%s.catlas.%d.gxt' % (_basename, _radius)
    _catmxt = '%s.catlas.%d.mxt' % (_basename, _radius)
    _catgxt = os.path.join(args.catlas_prefix, _catgxt)
    _catmxt = os.path.join(args.catlas_prefix, _catmxt)
    _catlas = CAtlas.read(_catgxt, _catmxt, _radius)    

    ### get the labels from the original graph

    # here, 'orig_to_labels' is a dictionary mapping De Bruijn graph node IDs
    # to a list of labels for each node, and 'orig_sizes' is the size of the
    # original nodes.
    #
    #   orig_to_labels[dbg_node_id] => list of [label_ids]
    _dbg_graph = '%s.gxt' % (_basename)
    _dbg_graph = os.path.join(args.catlas_prefix, _dbg_graph)

    orig_sizes, orig_to_labels = \
      load_orig_sizes_and_labels(_dbg_graph)

    ### backtrack the leaf nodes to the domgraph

    # here, 'dom_to_orig' is a dictionary mapping domination nodes to
    # a list of original vertices in the De Bruijn graph.
    #
    #   dom_to_orig[dom_node_id] => list of [orig_node_ids]

    dom_to_orig = load_dom_to_orig(catlas.assignment_vxt)


    ### load mxt

    # 'mxt_dict' is a dictionary mapping catlas node IDs to MinHash
    # objects.

    if not args.quiet:
        print('reading mxt file', catlas.catlas_mxt)

    mxt_dict = VertexDict()
    for n in _catlas.nodes():
        mxt_dict[n.id] = n.minhash

    ### load search mh

    if not args.quiet:
        print('reading mh file', args.mh_file)

    query_mh = load_mh_dump(args.mh_file)

    ### next, find the relevant catlas nodes using the MinHash.

    if not args.quiet:
        print('searching catlas minhashes w/%s' % args.mh_file)

    print('')
    print('search strategy:', args.strategy, args.searchlevel)

    if args.strategy == 'bestnode':
        match_nodes = _catlas.query_best_match(query_mh)
    elif args.strategy == 'searchlevel':
        match_nodes = _catlas.query_level(query_mh, args.searchlevel)
    elif args.strategy == 'gathermins':
        match_nodes = _catlas.query_gather_mins(query_mh, args.searchlevel)
    elif args.strategy == 'gathermins2':
        match_nodes = _catlas.query_gather_mins(query_mh, args.searchlevel, expand=True)
    elif args.strategy == 'frontier-jacc':
        match_nodes  = _catlas.query(query_mh, 0, CAtlas.Scoring.height_weighted_jaccard, CAtlas.Selection.largest_weighted_intersection, CAtlas.Refinement.greedy_coverage)                
    elif args.strategy == 'frontier-jacc-bl':
        match_nodes  = _catlas.query_blacklist(query_mh, 0, CAtlas.Scoring.height_weighted_jaccard, CAtlas.Selection.largest_weighted_intersection, CAtlas.Refinement.greedy_coverage)           
    elif args.strategy == 'frontier-height':
        match_nodes  = _catlas.query(query_mh, 0, CAtlas.Scoring.avg_height, CAtlas.Selection.largest_intersection_height, CAtlas.Refinement.greedy_coverage)
    elif args.strategy == 'frontier-height-bl':
        match_nodes  = _catlas.query_blacklist(query_mh, 0, CAtlas.Scoring.avg_height, CAtlas.Selection.largest_intersection_height, CAtlas.Refinement.greedy_coverage)        
    elif args.strategy == 'frontier-worst':
        match_nodes  = _catlas.query(query_mh, 0, CAtlas.Scoring.worst_node, CAtlas.Selection.largest_weighted_intersection, CAtlas.Refinement.greedy_coverage)        
    elif args.strategy == 'frontier-worst-bl':
        match_nodes  = _catlas.query_blacklist(query_mh, 0, CAtlas.Scoring.worst_node, CAtlas.Selection.largest_weighted_intersection, CAtlas.Refinement.greedy_coverage)                
    else:
        print('\n*** search strategy not understood:', args.strategy)
        sys.exit(-1)

    leaves = set()
    for n in _catlas.nodes(match_nodes):
        leaves.update(n.shadow())

    if not args.quiet:
        print('found %d domgraph leaves under catlas nodes %s' % \
              (len(leaves), match_nodes))

    dbg_nodes = set()
    for dom_node in leaves:
        dbg_nodes.update(dom_to_orig[dom_node])

    all_dbg_nodes = set()
    for v in dom_to_orig.values():
        all_dbg_nodes.update(v)

    print('found XXX', len(dbg_nodes))
    print('of', len(all_dbg_nodes))

    print(dbg_nodes)

    # grab the hashes from the final .mxt

    _dbg_mxt = '%s.mxt' % (_basename)
    _dbg_mxt = os.path.join(args.catlas_prefix, _dbg_mxt)

    sweep_kmers = set()
    for line in open(_dbg_mxt):
        node_id, rest = line.split(',', 1)
        node_id = int(node_id)

        if node_id in dbg_nodes:
            rest = map(int, rest.split())
            sweep_kmers.update(rest)
    print('got %d kmers to sweep' % (len(sweep_kmers),))

    if args.output_fp:
        output = map(str, sweep_kmers)
        output = "\n".join(output)
        args.output_fp.write(output)

    sys.exit(0)


if __name__ == '__main__':
    main()
