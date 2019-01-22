

import re
import exrex
import random
import itertools
from pprint import pprint
from itertools import chain

import textx
import arpeggio

from example import METAMODEL


REGEX_MATCH_EXAMPLES = {
    'Lucas',
    'Jean-Charles',
    'Cunégonde',
    '007',
    '42',
    'Ah! Ah! Ah!',
    "I'm afraid i can't do that, Dave",
    "$><$ =?= Leia",
    "HOLY COW!",
    ">=",
    "This.Is.a-vALID.mAIL@address.i.swear.net",
    "This.Is.a-vALID.mAIL+filter@address.i.swear.net",
    'aValidPythonIdentifier_02342_éèàùìïüä',
    'aValidPythonIdentifier_02342',
    '"Any text, surrounded by double quote ! \o/"',
    "'Any text, surrounded by single quote ! \o/'",
}
REGEX_MATCH_EXAMPLES |= set(m.lower() for m in REGEX_MATCH_EXAMPLES)
REGEX_MATCH_EXAMPLES |= set(m.title() for m in REGEX_MATCH_EXAMPLES)


def print_obj(obj, *, level:int=1) -> print:
    for name, elem in obj.__dict__.items():
        if not name.startswith('__'):
            print('.\t', name.ljust(15), str(('"' + elem + '"') if isinstance(elem, str) else elem).ljust(60), type(elem))


def get_match_examples(regex:str) -> (str, str, str):
    """Return a tuple of 3 strings matched by given regex"""
    def get_matches():
        for example in REGEX_MATCH_EXAMPLES:
            if re.fullmatch(example, regex):
                yield example
    def nb_similarity(one:str, two:str) -> int:
        return sum(int(a == b) for a, b in zip(one, two))

    matches = set(get_matches())

    if len(matches) > 3:
        # detect those that are quite similar, keep in memory those we don't want
        to_discard = set()
        for one in matches:
            for two in matches:
                if nb_similarity(one, two) >= 10:  # TODO: why 10 ? Why not another ? (NOTE: normalize on size seems odd at first glance, i may be wrong)
                    matches -= two if len(one) > len(two) else one

    while len(matches) < 3:  # Well, that's restrictive… Let's use a rexex generator !
        # other lib to explore maybe: rstr: https://bitbucket.org/leapfrogdevelopment/rstr/
        matches.add(exrex.getone(regex))

    return tuple(sorted(tuple(matches)))  # keep it deterministic if no fallback on rexex


def doc_from_class(cls:object) -> str or None:
    """Return string containing the documentation of given class, or None if not any"""
    if not hasattr(cls, '__doc__'):
        return
    cls_doc = cls.__doc__
    if cls_doc is None:
        return
    if any(line.strip() == 'Not documented by textx-dsldoc.' for line in cls_doc.splitlines()):
        return
    # print(f'DOC: "{cls_doc}"')
    return cls_doc



# print(dir(METAMODEL))
# for name, elem in vars(METAMODEL).items():
    # print(name, elem)
    # print()
# print()


# for cls_name, cls in METAMODEL.user_classes.items():
    # print(f"\t{cls_name}: has {'' if doc_from_class(cls) else 'no '}doc, repr: {repr(cls)}")
# print()

# for name, elem in vars(METAMODEL._parser).items():
    # print('.\t', name, elem)

# print()

# for name, elem in vars(METAMODEL._parser.parser_model).items():
    # print('.\t', name, elem)

def search_for_regexes(parser_model:arpeggio.Sequence) -> [str]:
    """Yield regexes found along the name of the class matching it"""
    print('PARSER:', parser_model)
    print(dir(parser_model))
    for name, elem in vars(parser_model).items():
        print('.\t', name, elem)
    # for node in parser_model.nodes:
        # yield from search_for_regexes(node)

    yield from ()


first_nodes = METAMODEL._parser.parser_model.nodes
# print('NODES:', first_nodes)
# print(tuple(search_for_regexes(first_nodes[0])))


def contained_classes(textx_class) -> [object]:
    """Yield classes (textx, user or even regexes) contained in given class"""
    ...

def as_regex(textx_class) -> str or None:
    """Return None if given object does not represent a single regex.
    Return the regex if only one

    Basically, when looking around, i got the feeling that a textx class
    matching to a regex has the following attributes tree:

        <class 'example.Identifier'>
            |> _tx_attrs: OrderedDict([('id', <textx.metamodel.MetaAttr object at 0x…>)])  (note the len of 1)
            |> _tx_peg_rule <arpeggio.Sequence object at 0x…>
                |> nodes [<arpeggio.Sequence object at 0x…>]
                           |> nodes [<arpeggio.Sequence object at 0x…>]
                                      |> nodes [<arpeggio.RegExMatch object at 0x…>]

    The tree is linear, and the number of arpeggio.Sequence.nodes[0] access to
    perform seems to be stable at 2.

    """
    if not hasattr(textx_class, '_tx_attrs'):  return
    if len(textx_class._tx_attrs) == 1 and hasattr(textx_class, '_tx_peg_rule'):
        peg_rule = textx_class._tx_peg_rule
        while len(peg_rule.nodes) == 1 and isinstance(peg_rule.nodes[0], arpeggio.Sequence):
            peg_rule = peg_rule.nodes[0]
        if len(peg_rule.nodes) == 1:
            peg_rule = peg_rule.nodes[0]
        else:  return  # probably not a regex
        if isinstance(peg_rule, arpeggio.RegExMatch):
            return peg_rule.to_match


def render_arpeggio_sequence(seq:arpeggio.Sequence) -> str:
    """Return a string representation of argpeggio"""
    NESTEDS = (arpeggio.Optional, arpeggio.OneOrMore, arpeggio.ZeroOrMore)
    SPECIAL_REGEXES = {
        "[-+]?[0-9]+\\b": 'INT',
        "[^\\d\\W]\\w*\\b": 'ID',
        "(True|true|False|false|0|1)\\b": 'BOOL',
        '("(\\\\"|[^"])*")|(\\\'(\\\\\\\'|[^\\\'])*\\\')': 'STRING',
        "[+-]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][+-]?\\d+)?(?<=[\\w\\.])(?![\\w\\.])": 'FLOAT',
    }
    if isinstance(seq, arpeggio.StrMatch):
        return seq.to_match
    elif isinstance(seq, arpeggio.OrderedChoice):
        return '(' + ') OR ('.join(map(render_arpeggio_sequence, seq.nodes)) + ')'
    elif isinstance(seq, tuple(NESTEDS)):
        assert len(seq.nodes) == 1
        child = seq.nodes[0]
        print()
        print('CHILD:', child)
        print(dir(child))
        print(print_obj(child))
        child_repr = child._tx_class.__name__ if hasattr(child, '_tx_class') else render_arpeggio_sequence(child)
        # exit()
        if isinstance(seq, arpeggio.ZeroOrMore):
            return f'[{child_repr}_1{seq.sep or ""} …{seq.sep or ""} {child_repr}_n]'
        elif isinstance(seq, arpeggio.OneOrMore):
            return f'{child_repr}_1[{seq.sep or ""} …{seq.sep or ""} {child_repr}_n]'
        assert isinstance(seq, arpeggio.Optional)
        return f'[{child_repr}]'
    elif isinstance(seq, arpeggio.RegExMatch):
        if seq.to_match in SPECIAL_REGEXES:
            return SPECIAL_REGEXES[seq.to_match]
        return f'/{seq.to_match}/'
    assert isinstance(seq, arpeggio.Sequence), (seq, type(seq))
    return ' '.join(render_arpeggio_sequence(node) for node in seq.nodes)


def search_for_structure_info(textx_class, *, name=None, treated_classes:dict={}) -> dict:
    """Return dict of infos found along the name of the class matching it"""
    if textx_class in treated_classes:  # already treated
        return treated_classes[textx_class]
    treated_classes[textx_class] = outdict = {}
    if name:  outdict['name in parent'] = name
    if hasattr(textx_class, '__name__'):  outdict['name'] = textx_class.__name__
    regex = as_regex(textx_class)
    if regex:
        outdict['regex'] = name, regex
    elif isinstance(textx_class, textx.metamodel.MetaAttr):
        outdict['select'] = textx_class.mult, search_for_structure_info(textx_class.cls, name=name, treated_classes=treated_classes)
    elif not textx_class._tx_attrs and textx_class._tx_inh_by:  # it's a raw choice
        outdict['choice'] = tuple(
            search_for_structure_info(subclass, name=name, treated_classes=treated_classes)
            for subclass in textx_class._tx_inh_by
        )
    elif textx_class.__name__ in {'STRING', 'INT', 'FLOAT', 'ID', 'BOOL', 'NUMBER'}:
        outdict['type'] = textx_class
    else:
        outdict['children'] = []  # iterable of (name, structure)
        outdict['str'] = render_arpeggio_sequence(textx_class._tx_peg_rule)
        doc = doc_from_class(textx_class)
        # if doc:  outdict['doc'] = doc


        if name:
            print('CLS:', name, textx_class)
        else:
            print('CLS:', textx_class)
        print('\t', type(textx_class).__name__ == 'TextXMetaClass', textx_class.__name__)
        print(dir(textx_class))
        print_obj(textx_class)
        for name, obj in textx_class._tx_attrs.items():

            # target = obj
            # target = textx_class
            # target = textx_class._tx_peg_rule.nodes[0]
            target = textx_class._tx_peg_rule
            if isinstance(target, arpeggio.Sequence):
                for node in target.nodes:
                    if isinstance(node, arpeggio.StrMatch):
                        target = node
                        print()
                        print()
                        print()
                        print(target)
                        print(type(target))
                        print(dir(target))
                        print_obj(target)
            outdict['children'].append((name, search_for_structure_info(obj, name=name, treated_classes=treated_classes)))
    return outdict

print(dir(METAMODEL.rootcls))
# for name, elem in vars(METAMODEL.rootcls).items():
    # print('.\t', name, elem)
out = search_for_structure_info(METAMODEL.rootcls)
print(search_for_structure_info(METAMODEL.rootcls))
pprint(search_for_structure_info(METAMODEL.rootcls))
