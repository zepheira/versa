#versa.writer.md
"""
Render a Versa model as [Mermaid]()

Note: you'll probably want something like mermaid-cli

"""

# Need npm to install mermaid-cli, so see: https://nodejs.org/en/

import re
import sys
import os
import glob
import time
from itertools import islice
import logging

from slugify import slugify # pip install python-slugify

from amara3 import iri

from versa import I, VERSA_BASEIRI, ORIGIN, RELATIONSHIP, TARGET, VLABEL_REL, VTYPE_REL
from versa.driver import memory
from versa import VERSA_BASEIRI
from versa.reader.md import from_markdown
from versa.util import all_origins, lookup, labels


def abbreviate(rel, bases):
    for base in bases:
        abbr = iri.relativize(rel, base, subPathOnly=True)
        if abbr:
            if base is VERSA_BASEIRI:
                abbr = '@' + abbr
            return abbr
    return rel


def value_format(val):
    if isinstance(val, I):
        return str(val)
    else:
        return repr(val)


TAG_MAX_STEM_LENGTH = 12

def lookup_tag(obj, tag_map, label, is_node=True):
    '''
    '''
    stem = tag_map.get(obj)
    disambig = ''
    if stem is None:
        # FIXME: A bit wasteful here. We could just maintain the set after one-time creation
        existing_tags = set(tag_map.values())
        stem = str(obj).split('/')[-1]
        if len(stem) >= TAG_MAX_STEM_LENGTH:
            split_point = TAG_MAX_STEM_LENGTH // 2
            # Tried using '\u2026' but leads to Mermaid syntax error
            stem = stem[:split_point] + '...' + stem[-split_point:]

        disambig = 0
        while f'{stem}-{disambig}' in existing_tags:
            disambig += 1

        disambig = '' if not disambig else str(disambig)
        tag_map[obj] = f'{stem}{"-" if disambig else ""}{disambig}'

    asc_stem = slugify(stem)
    # Raw node ID
    node_id = f'{asc_stem}{disambig}'
    # Node label
    if label:
        # Implies its a resource
        if len(label) >= TAG_MAX_STEM_LENGTH:
            split_point = TAG_MAX_STEM_LENGTH // 2
            # Tried using '\u2026' but leads to Mermaid syntax error
            label = label[:split_point] + '...' + label[-split_point:]
        return f'{node_id}(fa:fa-tag {label})'

    label = f'{stem}{"-" if disambig else ""}{disambig}'
    if is_node:
        if isinstance(obj, I):
            return f'{node_id}({label})'
        else:
            return f'{node_id}[{label}]'
    else:
        return label


# TODO: Use stereotype to indicate @type
def write(model, out=None, base=None, propertybase=None, shorteners=None, logger=logging):
    '''
    models - input Versa model from which output is generated.
    '''
    assert out is not None #Output stream required
    shorteners = shorteners or {}

    resource_tags = {}
    property_tags = {}
    value_tags = {}

    out.write('graph TD\n')

    for o in all_origins(model):
        o_label = next(labels(model, o), None)
        o_tag = lookup_tag(o, resource_tags, o_label)
        for _, r, t, a in model.match(o):
            r_tag = lookup_tag(r, property_tags, None, is_node=False)
            if isinstance(t, I):
                t_label = next(labels(model, t), None)
                t_tag = lookup_tag(t, resource_tags, t_label)
            else:
                t_tag = lookup_tag(t, value_tags, None)

            out.write(f'    {o_tag} -->|{r_tag}| {t_tag}\n')
            #for k, v in a.items():
            #    abbr_k = abbreviate(k, all_propertybase)
            #    out.write('    * {0}: {1}\n'.format(k, value_format(v)))

        out.write('\n')
    return
