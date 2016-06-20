#versa.pipeline
'''
Framework for expressing transforms from one pattern of Versa links to another
This is especially useful if you've used a tool to extract Versa from some data
source but would like to tweak the interpretation of that data. It's also useful
for mapping from one vocabulary to another.

The concept is similar to XProc (http://en.wikipedia.org/wiki/XProc). You define
the overall transform in terms of transform steps or stages, implemented as
Python functions. Each function can have inputs, which might be simple Versa
scalars or even functions in themselves. The outputs are Versa scalars.

There is also a shared environment across the steps, called the context (`versa.context`).
The context includes a resource which is considered the origin for purposes
of linking, an input Versa model considered to be an overall input to the transform
and an output Versa model considered to be an overall output.
'''

#FIXME: Use __all__

import json
import itertools
import functools
import logging
#from enum import Enum #https://docs.python.org/3.4/library/enum.html
from collections import defaultdict, OrderedDict

#import amara3
from amara3 import iri
#from amara3.util import coroutine

from versa import I, VERSA_BASEIRI, ORIGIN, RELATIONSHIP, TARGET, ATTRIBUTES
from versa import util
from versa.util import simple_lookup, OrderedJsonEncoder
from versa.driver import memory

from versa.contrib.datachefids import idgen as default_idgen, FROM_EMPTY_HASH

VTYPE_REL = I(iri.absolutize('type', VERSA_BASEIRI))

class context(object):
    #Default way to create a model for the transform output, if one is not provided
    transform_factory = memory.connection

    #Note: origin was eliminated; not really needed since the origin of current_link can be used
    def __init__(self, current_link, input_model, output_model=None, base=None, variables=None, extras=None, idgen=None, existing_ids=None):
        '''
        current_link - one of the links in input_model, a key reference for the transform
        input_model - Versa model treated as overall input to the transform
        output_model - Versa model treated as overall output to the transform; if None an empty model is created
        base - reference base IRI, e.g. used to resolve created resources
        '''
        self.current_link = current_link
        self.input_model = input_model
        self.output_model = output_model or context.transform_factory()
        self.base = base
        self.variables = variables or {}
        self.extras = extras or {}
        #FIXME: idgen requires a base IRI. Think this over.
        self.idgen = idgen or default_idgen(base)
        self.existing_ids = existing_ids or set()

    def copy(self, current_link=None, input_model=None, output_model=None, base=None, variables=None, extras=None, idgen=None, existing_ids=None):
        current_link = current_link if current_link else self.current_link
        input_model = input_model if input_model else self.input_model
        output_model = output_model if output_model else self.output_model
        base = base if base else self.base
        variables = variables if variables else self.variables
        extras = extras if extras else self.extras
        idgen = idgen if idgen else self.idgen
        existing_ids = existing_ids if existing_ids else self.existing_ids
        return context(current_link=current_link, input_model=input_model, output_model=output_model, base=base, extras=extras, idgen=idgen, existing_ids=existing_ids)


def materialize_entity(ctx, etype, unique=None):
    '''
    Routine for creating a BIBFRAME resource. Takes the entity (resource) type and a data mapping
    according to the resource type. Implements the Libhub Resource Hash Convention
    As a convenience, if a vocabulary base is provided in the context, concatenate it to etype and the data keys

    ctx - context information governing creation fo the mew entity
    etype - type IRI for th enew entity
    unique - scalar or ordered dict of data to use in generating its unique ID, or None in which case one is just randomly generated
    '''
    params = {}
    if ctx.base:
        etype = ctx.base + etype
    unique_full = unique
    if isinstance(unique, OrderedDict):
        unique_full = OrderedDict()
        for (k, v) in unique.items():
            unique_full[ k if iri.is_absolute(k) else iri.absolutize(k, ctx.base) ] = v

    if unique_full:
        plaintext = json.dumps([etype, unique_full], cls=OrderedJsonEncoder)
        eid = ctx.idgen.send(plaintext)
    else:
        #We only have a type; no other distinguishing data. Generate a random hash
        eid = next(ctx.idgen)
    return eid


def link(rel, res=False, attributes=None):
    '''
    Action function generator to copy/preserve the label of the relationship to be added to the link space
    '''
    attributes = attributes or {}
    def _rename(ctx):
        (o, r, t, a) = ctx.current_link
        if res:
            try:
                t = I(t)
            except ValueError:
                return []

        out_attrs = {}
        for k, v in attributes.items():
            k = k(ctx) if callable(k) else k
            #If k is a list of contexts use it to dynamically execute functions
            if isinstance(k, list):
                if k and isinstance(k[0], context):
                    for newctx in k:
                        #Presumably the function in question will generate any needed links in the output model
                        v(newctx)
                    continue

            #import traceback; traceback.print_stack() #For looking up the call stack e.g. to debug nested materialize
            #Check that the attributes key is not None, which is a signal not to
            #generate the item. For example if the key is an ifexists and the
            #test expression result is False, it will come back as None,
            #and we don't want to run the v function
            if k:
                new_current_link = (o, k, ctx.current_link[TARGET], ctx.current_link[ATTRIBUTES])
                newctx = ctx.copy(current_link=new_current_link)
                v = v(newctx) if callable(v) else v

                #If k or v come from pipeline functions as None it signals to skip generating anything else for this link item
                if v is not None:
                    v = v(newctx) if callable(v) else v
                    #FIXME: Fix properly, by slugifying & making sure slugify handles all-numeric case
                    if k.isdigit(): k = '_' + k
                    if isinstance(v, list):
                        for valitems in v:
                            if valitems:
                                #out_attrs[k] = valitems
                                out_attrs[I(iri.absolutize(k, newctx.base))] = valitems
                    else:
                        #out_attrs[I(iri.absolutize(k, newctx.base))] = v
                        out_attrs[k] = v

        ctx.output_model.add(I(o), I(iri.absolutize(rel, ctx.base)), t, out_attrs)
        return
    return _rename


def links(origin, rel, target, attributes=None):
    '''
    Action function generator to create a new link in the output
    '''
    def _links(ctx):
        _origin = origin(ctx) if callable(origin) else origin
        _origin = _origin if isinstance(_origin, set) else set([_origin])
        _rel = rel(ctx) if callable(rel) else rel
        _rel = _rel if isinstance(_rel, set) else set([_rel])
        _target = target(ctx) if callable(target) else target
        _target = _target if isinstance(_target, set) else set([_target])
        _attributes = attributes(ctx) if callable(attributes) else {} if attributes is None else attributes
        #(origin, rel, target, attributes) = ctx.current_link

        for (o, r, t, a) in [ (o, r, t, a) for o in _origin for r in _rel for t in _target for a in [_attributes] ]:
            ctx.output_model.add(o, r, t, a)
        return
    return _links


def var(name):
    '''
    Action function generator to retrieve a variable from context
    '''
    def _var(ctx):
        return ctx.variables.get(name)
    return _var


def target():
    '''
    Action function generator to return the target of the context's current link

    :return: target of the context's current link
    '''
    #Action function generator to multiplex a relationship at processing time
    def _target(ctx):
        '''
        Versa action function Utility to return the target of the context's current link

        :param ctx: Versa context used in processing (e.g. includes the prototype link
        :return: Target of the context's current link
        '''
        return ctx.current_link[TARGET]
    return _target


def values(*rels):
    '''
    Action function generator to compute a set of relationships from criteria

    :param rels: List of relationships to compute
    :return: Versa action function to do the actual work
    '''
    #Action function generator to multiplex a relationship at processing time
    def _values(ctx):
        '''
        Versa action function Utility to specify a list of relationships

        :param ctx: Versa context used in processing (e.g. includes the prototype link
        :return: Tuple of key/value tuples from the attributes; suitable for hashing
        '''
        computed_rels = [ rel(ctx) if callable(rel) else rel for rel in rels ]
        return computed_rels
    return _values


def ifexists(test, value, alt=None):
    '''
    Action function generator providing an if/then/else type primitive
    :param test: Expression to be tested to determine the branch path
    :param value: Expression providing the result if test is true
    :param alt: Expression providing the result if test is false
    :return: Versa action function to do the actual work
    '''
    def _ifexists(ctx):
        '''
        Versa action function Utility to specify a list of relationships

        :param ctx: Versa context used in processing (e.g. includes the prototype link)
        :return: Value computed according to the test expression result
        '''
        _test = test(ctx) if callable(test) else test
        if _test:
            return value(ctx) if callable(value) else value
        else:
            return alt(ctx) if callable(alt) else alt
    return _ifexists


def foreach(origin=None, rel=None, target=None, attributes=None):
    '''
    Action function generator to compute a combination of links and fun the

    :return: Versa action function to do the actual work
    '''
    def _foreach(ctx):
        '''
        Versa action function utility to compute a list of values from a list of expressions

        :param ctx: Versa context used in processing (e.g. includes the prototype link)
        '''
        _origin = origin(ctx) if callable(origin) else origin
        _rel = rel(ctx) if callable(rel) else rel
        _target = target(ctx) if callable(target) else target
        _attributes = attributes(ctx) if callable(attributes) else attributes
        (o, r, t, a) = ctx.current_link
        o = [o] if _origin is None else (_origin if isinstance(_origin, list) else [_origin])
        r = [r] if _rel is None else (_rel if isinstance(_rel, list) else [_rel])
        t = [t] if _target is None else (_target if isinstance(_target, list) else [_target])
        #a = [a] if _attributes is None else _attributes
        a = [a] if _attributes is None else (_attributes if isinstance(_attributes, list) else [_attributes])
        #print([(curr_o, curr_r, curr_t, curr_a) for (curr_o, curr_r, curr_t, curr_a)
        #            in product(o, r, t, a)])
        return [ ctx.copy(current_link=(curr_o, curr_r, curr_t, curr_a))
                    for (curr_o, curr_r, curr_t, curr_a)
                    in itertools.product(o, r, t, a) ]
        #for (curr_o, curr_r, curr_t, curr_a) in product(origin or [o], rel or [r], target or [t], attributes or [a]):
        #    newctx = ctx.copy(current_link=(curr_o, curr_r, curr_t, curr_a))
            #ctx.output_model.add(I(objid), VTYPE_REL, I(iri.absolutize(_typ, ctx.base)), {})
    return _foreach


def materialize(typ, rel=None, derive_origin=None, unique=None, links=None, inverse=False, split=None, attributes=None):
    '''
    Create a new resource related to the origin
    '''
    links = links or {}
    attributes = attributes or {}
    def _materialize(ctx):
        #FIXME: Part of the datachef sorting out
        if not ctx.idgen: ctx.idgen = idgen
        _typ = typ(ctx) if callable(typ) else typ
        _rel = rel(ctx) if callable(rel) else rel
        (o, r, t, a) = ctx.current_link
        #FIXME: On redesign implement split using function composition instead
        targets = [ sub_t.strip() for sub_t in t.split(split) ] if split else [t]
        #Conversions to make sure we end up with a list of relationships out of it all
        if _rel is None:
            _rel = [r]
        rels = _rel if isinstance(_rel, list) else ([_rel] if rel else [])
        objids = []
        for target in targets:
            ctx_ = ctx.copy(current_link=(o, r, target, a))
            if derive_origin:
                #Have been given enough info to derive the origin from context. Ignore origin in current link
                o = derive_origin(ctx_)
            computed_unique = unique(ctx_) if callable(unique) else unique
            objid = materialize_entity(ctx_, _typ, unique=computed_unique)
            objids.append(objid)
            for curr_rel in rels:
                #FIXME: Fix this properly, by slugifying & making sure slugify handles all numeric case (prepend '_')
                curr_rel = '_' + curr_rel if curr_rel.isdigit() else curr_rel
                if curr_rel:
                    if inverse:
                        ctx_.output_model.add(I(objid), I(iri.absolutize(curr_rel, ctx_.base)), I(o), {})
                    else:
                        ctx_.output_model.add(I(o), I(iri.absolutize(curr_rel, ctx_.base)), I(objid), {})
            #print((objid, ctx_.existing_ids))
            if objid not in ctx_.existing_ids:
                if _typ: ctx.output_model.add(I(objid), VTYPE_REL, I(iri.absolutize(_typ, ctx_.base)), {})
                #FIXME: Should we be using Python Nones to mark blanks, or should Versa define some sort of null resource?
                for k, v in links.items():
                    k = k(ctx_) if callable(k) else k
                    #If k is a list of contexts use it to dynamically execute functions
                    if isinstance(k, list):
                        if k and isinstance(k[0], context):
                            for newctx in k:
                                #Presumably the function in question will generate any needed links in the output model
                                v(newctx)
                            continue

                    #import traceback; traceback.print_stack() #For looking up the call stack e.g. to debug nested materialize
                    #Check that the links key is not None, which is a signal not to
                    #generate the item. For example if the key is an ifexists and the
                    #test expression result is False, it will come back as None,
                    #and we don't want to run the v function
                    if k:
                        new_current_link = (I(objid), k, ctx.current_link[TARGET], ctx.current_link[ATTRIBUTES])
                        newctx = ctx.copy(current_link=new_current_link)
                        v = v(newctx) if callable(v) else v

                        #If k or v come from pipeline functions as None it signals to skip generating anything else for this link item
                        if v is not None:
                            v = v(newctx) if callable(v) else v
                            #FIXME: Fix properly, by slugifying & making sure slugify handles all-numeric case
                            if k.isdigit(): k = '_' + k
                            if isinstance(v, list):
                                for valitems in v:
                                    if valitems:
                                        ctx.output_model.add(I(objid), I(iri.absolutize(k, newctx.base)), valitems, {})
                            else:
                                ctx.output_model.add(I(objid), I(iri.absolutize(k, newctx.base)), v, {})
                ctx.existing_ids.add(objid)
        return objids

    return _materialize


def res(arg):
    '''
    Convert the argument into an IRI ref
    '''
    def _res(ctx):
        _arg = arg(ctx) if callable(arg) else arg
        return I(arg)
    return _res


def compose(*funcs):
    '''
    Compose an ordered list of functions. Args of a,b,c,d evaluates as a(b(c(d(ctx))))
    '''
    def _compose(ctx):
        # last func gets context, rest get result of previous func
        _result = funcs[-1](ctx)
        for f in reversed(funcs[:-1]):
            _result = f(_result)

        return _result
    return _compose


def discard():
    '''
    Action function generator that's pretty much a no-op. Just ignore the proposed link set

    :return: None
    '''
    def _discard(ctx): return
    return _discard

# ----
# Still needed?


class resource(object):
    def __init__(self, ctx):
        self._origin = ctx.current_link[ORIGIN]
        self._input_model = ctx.input_model
        self._base = ctx.base
        return

    def follow(self, rel):
        return simple_lookup(self._input_model, self._origin, I(iri.absolutize(rel, self._base)))


def origin(ctx):
    return resource(ctx.current_link[ORIGIN], ctx.input_model)


def run(pycmds):
    def _run(ctx):
        gdict = {
            'origin': ctx.current_link[ORIGIN],
            #'origin': resource(ctx),
            #'origin': resource(link[ORIGIN], ctx),
            'target': ctx.current_link[TARGET],
        }
        result = eval(pycmds, gdict)
        return result
    return _run
