#!/usr/bin/env python
#-*- mode: python -*-
# csv_to_bibframe.py

'''
Demo of Versa Pipeline. Converts a CSV with book info into BIBFRAME Lite

You might first want to be familar with dc_to_schemaorg.py
and csv_to_schemaorg.py

python demo/csv_to_bibframe.py demo/books.csv

http://bibfra.me/
'''

import sys
import random
import warnings
import functools
from pathlib import Path

import click # Cmdline processing tool. pip install click

from amara3 import iri

from versa import ORIGIN, RELATIONSHIP, TARGET
from versa import I, VERSA_BASEIRI, VTYPE_REL, VLABEL_REL
from versa import util
from versa.driver.memory import newmodel
from versa.reader.csv_polyglot import parse_iter
from versa.writer import md, mermaid
from versa.pipeline import *
from versa.contrib.datachefids import idgen as default_idgen

BOOK_NS = I('https://example.org/')
IMPLICIT_NS = I('http://example.org/vocab/')
BF_NS = I('http://bibfra.me/')


from versa.pipeline import *

FINGERPRINT_RULES = {
    # Fingerprint DC book by ISBN & output resource will be a SCH Book

    # Outermost parens here are not really needed, used for formatting.
    # You can use an actual tuple here, though, to trigger multiple
    # rules per matched type
    IMPLICIT_NS('Book'): ( 
        materialize(BF_NS('Instance'),
            unique=[
                (BF_NS('isbn'), follow(IMPLICIT_NS('identifier'))),
            ],
            links=[
                (BF_NS('provenance'), var('provenance')),
                (BF_NS('instantiates'),
                    materialize(BF_NS('Work'),
                        unique=[
                            (BF_NS('name'), follow(IMPLICIT_NS('title'))),
                        ],
                    ),
                )
            ]
        )
    )
}


# Data transformation rules. In general this is some sort of link from an
# Input pattern being matched to output generated by Versa pipeline actions

# In this case we use a dict of expected relationships from fingerprinted
# resources dict values are the action function that updates the output model
# by acting on the provided context (in this case just the triggered
# relationship in the input model)

# Work & instance types
WT = BF_NS('Work')
IT = BF_NS('Instance')


DC_TO_SCH_RULES = {
    # Rules that are the same regardless of matched output resource type
    IMPLICIT_NS('title'): link(rel=BF_NS('name')),

    # Rules differentiated by matched output resource type
    (IMPLICIT_NS('author'), WT): materialize(BF_NS('Person'),
                                BF_NS('creator'),
                                unique=[
                                    (BF_NS('name'), attr(IMPLICIT_NS('name'))),
                                    (BF_NS('birthDate'), attr(IMPLICIT_NS('date'))),
                                ],
                                links=[
                                    (BF_NS('name'), attr(IMPLICIT_NS('name'))),
                                    (BF_NS('birthDate'), attr(IMPLICIT_NS('date'))),
                                ]
    ),
}


LABELIZE_RULES = {
    # Labels come from input model's DC name rels
    BF_NS('Book'): follow(BF_NS('name'))
}


# Just use Python's built-in string.format()
# Could also use e.g. Jinja
VLITERATE_TEMPLATE = '''\
# @docheader

* @iri:
    * @base: https://example.org/
    * @schema: http://example.org/vocab/

# /{ISBN} [Book]

* title: {Title}
* author:
    * name: {Author}
    * date: {Author_date}
* publisher:
    * name: {Publisher}
    * date: {Pub_date}
* identifier: {ISBN}
    * type: isbn
'''


class csv_bibframe_pipeline(definition):
    def __init__(self):
        '''
        csv_bibframe_pipeline initializer
        '''
        self._provenance = I('http://example.com/SOME_CSV_FILE')
        super().__init__()

    @stage(1)
    def fingerprint(self):
        '''
        Generates fingerprints from the source model

        Result of the fingerprinting phase is that the output model shows
        the presence of each resource of primary interest expected to result
        from the transformation, with minimal detail such as the resource type
        '''
        # Prepare a root context
        ctx_vars = {'provenance': self._provenance}
        ctx = DUMMY_CONTEXT.copy(variables=ctx_vars)

        # Apply a common fingerprinting strategy using rules defined above
        new_rids = self.fingerprint_helper(FINGERPRINT_RULES, root_context=ctx)

        # In real code following lines could be simplified to: return bool(new_rids)
        if not new_rids:
            # Nothing found to process, so ret val set to False
            # This will abort pipeline processing of this input & move on to the next, if any
            return False

        # ret val True so pipeline run will continue for this input
        return True


    @stage(2)
    def main_transform(self):
        '''
        Executes the main transform rules to go from input to output model
        '''
        # Apply a common transform strategy using rules defined above
        # 
        def missed_rel(link):
            '''
            Callback to handle cases where a transform wasn't found to match a link (by relationship) in the input model
            '''
            warnings.warn(f'Unknown, so unhandled link. Origin :{link[ORIGIN]}. Rel: {link[RELATIONSHIP]}')

        new_rids = self.transform_by_rel_helper(DC_TO_SCH_RULES, handle_misses=missed_rel)
        return True


    @stage(3)
    def labelize(self):
        '''
        Executes a utility rule to create labels in output model for new (fingerprinted) resources
        '''
        # XXX Check if there's already a label?
        # Apply a common transform strategy using rules defined above
        def missed_label(origin, type):
            '''
            Callback to handle cases where a transform wasn't found to match a link (by relationship) in the input model
            '''
            warnings.warn(f'No label generated for: {origin}')
        labels = self.labelize_helper(LABELIZE_RULES, handle_misses=missed_label)
        return True


@click.command()
@click.argument('source')
def main(source):
    'Transform CSV SOURCE file to BF Lite in Versa'
    ppl = csv_bibframe_pipeline()
    input_model = newmodel()
    with open(source) as csvfp:
        for row_model in parse_iter(csvfp, VLITERATE_TEMPLATE):
            if row_model: input_model.update(row_model)

    # Debug print of input model
    # md.write([input_model], out=sys.stdout)
    output_model = ppl.run(input_model=input_model)
    print('Low level JSON dump of output data model: ')
    util.jsondump(output_model, sys.stdout)
    print('\n') # 2 CRs
    print('Versa literate form of output: ')
    md.write(output_model, out=sys.stdout)

    print('Diagram from extracted a sample: ')
    out_resources = []
    for vs in ppl.fingerprints.values():
        out_resources.extend(vs)
    ITYPE = BF_NS('Instance')
    instances = [ r for r in out_resources if ITYPE in util.resourcetypes(output_model, r) ]
    zoomed, _ = util.zoom_in(output_model, random.choice(instances), depth=2)
    mermaid.write(zoomed)
    md.write(zoomed)


if __name__ == '__main__':
    main()
