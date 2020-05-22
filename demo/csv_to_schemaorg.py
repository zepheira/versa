#!/usr/bin/env python
#-*- mode: python -*-
# csv_to_schemaorg.py

'''
Demo of Versa Pipeline. Converts a CSV with book info into Schema.org

You might first want to be familar with dc_to_schemaorg.py, which has
more comments on basics and doesn't bother with details such as
 command line

python demo/csv_to_schemaorg.py demo/books.csv

https://schema.org/Book
'''

import sys
import warnings
from pathlib import Path

import click # Cmdline processing tool. pip install click

from amara3 import iri

from versa import ORIGIN, RELATIONSHIP, TARGET
from versa import I, VERSA_BASEIRI, VTYPE_REL, VLABEL_REL
from versa import util
from versa.driver import memory
from versa.reader.csv_polyglot import parse
from versa.writer import md as md
from versa.pipeline import *
from versa.contrib.datachefids import idgen as default_idgen

BOOK_NS = I('https://example.org/')
IMPLICIT_NS = I('http://example.org/vocab/')
SCH_NS = I('https://schema.org/')


from versa.pipeline import *

FINGERPRINT_RULES = {
    # Fingerprint DC book by ISBN & output resource will be a SCH Book
    IMPLICIT_NS('Book'): materialize(SCH_NS('Book'),
                        unique=[
                            (SCH_NS('isbn'), follow(IMPLICIT_NS('identifier'))),
                        ]
    )
}


# Data transformation rules. In general this is some sort of link from an
# Input pattern being matched to output generated by Versa pipeline actions

# In this case we use a dict of expected relationships from fingerprinted
# resources dict values are the action function that updates the output model
# by acting on the provided context (in this case just the triggered
# relationship in the input model)

DC_TO_SCH_RULES = {
    IMPLICIT_NS('title'): link(rel=SCH_NS('name')),
    IMPLICIT_NS('creator'): materialize(SCH_NS('Person'),
                          unique=[
                              (SCH_NS('name'), attr(IMPLICIT_NS('name'))),
                              (SCH_NS('birthDate'), attr(IMPLICIT_NS('date'))),
                          ],
                          links=[
                              (SCH_NS('name'), attr(IMPLICIT_NS('name'))),
                              (SCH_NS('birthDate'), attr(IMPLICIT_NS('date'))),
                          ]
    ),
}


LABELIZE_RULES = {
    # Labels come from input model's DC name rels
    SCH_NS('Book'): follow(SCH_NS('name'))
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
* creator:
    * name: {Author}
    * date: {Author_date}
* publisher:
    * name: {Publisher}
    * date: {Pub_date}
* identifier: {ISBN}
    * type: isbn
'''


class csv_schema_pipeline(definition):

    @stage(1)
    def fingerprint(self):
        '''
        Generates fingerprints from the source model

        Result of the fingerprinting phase is that the output model shows
        the presence of each resource of primary interest expected to result
        from the transformation, with minimal detail such as the resource type
        '''
        # Apply a common fingerprinting strategy using rules defined above
        new_rids = self.fingerprint_helper(FINGERPRINT_RULES)

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
    'Transform CSV SOURCE file to Schema.org in Versa'
    ppl = csv_schema_pipeline()
    input_model = memory.connection()
    with open(source) as csvfp:
        parse(csvfp, VLITERATE_TEMPLATE, input_model)

    # Debug print of input model
    # md.write([input_model], out=sys.stdout)
    output_model = ppl.run(input_model=input_model)
    print('Resulting record Fingerprints:', ppl.fingerprints)
    print('Low level JSON dump of output data model: ')
    util.jsondump(output_model, sys.stdout)
    print('Versa literate form of output: ')
    md.write([output_model], out=sys.stdout)


if __name__ == '__main__':
    main()
