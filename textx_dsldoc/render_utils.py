"""Utilitaries to render a grammar.

"""

import re
import exrex
import random
import itertools
from pprint import pprint
from itertools import chain

import textx
import arpeggio



REGEX_MATCH_EXAMPLES = {
    'CamelCaseWith5Words',
    'UPPER_CASE_WITH_5_WORDS',
    'snake_case_with_5_words',
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
    "'Any text, with utf-8 ■▨ ϶ ⅀ ⇎'",
    '"Any text, with accents ìïäüèàù"',
    "'Any text, with accents ìïäüèàù and utf-8 ■▨ ϶ ⅀ ⇎'",
    '"multiline\ntext, with \nutf-8 ■▨ ϶ \n ⅀ ⇎"',
    '"multiline\ntext"',
    '~/a/path/to/a/.dotfile',
    '~/a/path/to/a/file',
    '/a/path/to/a/file',
    'a/relative/path/to/a/file',
    'a/relative/path/to/a/.dotfile',
    '../../a/relative/path/to/a/.dotfile',
    '../../a/relative/path/to/a/file',
}
REGEX_MATCH_EXAMPLES |= set(m.lower() for m in REGEX_MATCH_EXAMPLES)
REGEX_MATCH_EXAMPLES |= set(m.title() for m in REGEX_MATCH_EXAMPLES)


def print_obj(obj, *, level:int=1) -> print:
    print('PROBJ:', obj, type(obj))
    print(dir(obj))
    for name, elem in obj.__dict__.items():
        if not name.startswith('__'):
            print('.\t', name.ljust(15), str(('"' + elem + '"') if isinstance(elem, str) else elem).ljust(60), type(elem))


def get_match_examples(regex:str, amount:int=3) -> (str, str, str):
    """Return a tuple of 3 strings matched by given regex"""
    def get_matches():
        for example in REGEX_MATCH_EXAMPLES:
            if re.fullmatch(regex, example):
                yield example
    def similarity(one:str, two:str) -> int:
        size = min(len(one), len(two))
        return sum(int(a == b) for a, b in zip(one, two)) / size

    matches = set(get_matches())

    for similarity_threshold in (0.6, 0.5, 0.4, 0.3, 0.2, 0.1):
        while amount and len(matches) > amount:
            # detect those that are quite similar, keep in memory those we don't want
            for one in set(matches):
                for two in set(matches) - {one}:
                    if similarity(one, two) >= 0.4:
                        removing = two if len(one) > len(two) else one
                        # print(f'REMOVING {removing} from {matches} because similarity({one}, {two}) == {similarity(one, two)}')
                        matches -= {removing}
                        break
            else:  # no similarity found
                break
    while amount and len(matches) > amount:
        matches -= {random.choice(tuple(matches))}

    while amount and len(matches) < amount:  # Well, that's restrictive… Let's use a rexex generator !
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
    if 'Dynamically created class. Each textX rule will result in' in cls_doc:
        return  # that's the default doc associated with non-user classes
    # print(f'DOC: "{cls_doc}"')
    return cls_doc


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


SPECIAL_REGEXES = {
    'ID': "[^\\d\\W]\\w*\\b",
    'INT': "[-+]?[0-9]+\\b",
    'BOOL': "(True|true|False|false|0|1)\\b",
    'FLOAT': "[+-]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][+-]?\\d+)?(?<=[\\w\\.])(?![\\w\\.])",
    'STRING': '("(\\\\"|[^"])*")|(\\\'(\\\\\\\'|[^\\\'])*\\\')',
}
SPECIAL_REGEXES_REV = {v: k for k, v in SPECIAL_REGEXES.items()}


def render_regex(regex:str, examples:iter=None) -> str:
    """Render given regex in HTML"""
    if not examples:  examples = tuple(get_match_examples(regex))
    from urllib import parse
    BASE_URL = "https://pythex.org/?regex={regex}&test_string={test}"
    regurl = BASE_URL.format(regex=parse.quote(regex),
                             test=parse.quote('\n'.join(examples)))
    return f'[`/{regex}/`]({regurl})'


def render_arpeggio_sequence(seq:arpeggio.Sequence) -> (str, (...)):
    """Return tree of string representation of argpeggio"""
    NESTEDS = (arpeggio.Optional, arpeggio.OneOrMore, arpeggio.ZeroOrMore)
    if isinstance(seq, arpeggio.StrMatch):
        return str, seq.to_match
    elif isinstance(seq, arpeggio.OrderedChoice):
        return 'choice', tuple(map(render_arpeggio_sequence, seq.nodes))
    elif isinstance(seq, tuple(NESTEDS)):
        assert len(seq.nodes) == 1
        child = seq.nodes[0]
        # print()
        # print('CHILD:', child)
        # print(dir(child))
        # print(print_obj(child))
        child_repr = child._tx_class.__name__ if hasattr(child, '_tx_class') else render_arpeggio_sequence(child)
        # exit()
        if isinstance(seq, arpeggio.ZeroOrMore):
            return '0..*', child_repr, seq.sep
        elif isinstance(seq, arpeggio.OneOrMore):
            return '1..*', child_repr, seq.sep
        assert isinstance(seq, arpeggio.Optional)
        return '0..1', child_repr
    elif isinstance(seq, arpeggio.RegExMatch):
        for target, special_regex in SPECIAL_REGEXES.items():
            if seq.to_match == special_regex:
                return 'special regex', target.lower()
        return 'regex', seq.to_match
    assert isinstance(seq, arpeggio.Sequence), (seq, type(seq))
    return tuple(map(render_arpeggio_sequence, seq.nodes))


def search_for_structure_info(textx_class, *, name=None, treated_classes:dict={}) -> (dict, dict):
    """Return dict of infos found along the name of the class matching it,
    and dict mapping class name with content

    """
    if textx_class in treated_classes:  # already treated
        if name:  treated_classes[textx_class]['names in parent'].add(name)
        return treated_classes[textx_class], treated_classes
    treated_classes[textx_class] = outdict = {'names in parent': set()}
    if name:  outdict['names in parent'].add(name)
    if hasattr(textx_class, '__name__'):  outdict['name'] = textx_class.__name__
    regex = as_regex(textx_class)
    if regex:
        outdict['regex'] = name, regex
    elif isinstance(textx_class, textx.metamodel.MetaAttr):
        outdict['select'] = textx_class.mult, search_for_structure_info(textx_class.cls, name=name, treated_classes=treated_classes)[0]
    elif not textx_class._tx_attrs and textx_class._tx_inh_by:  # it's a raw choice
        outdict['choice'] = tuple(
            search_for_structure_info(subclass, name=name, treated_classes=treated_classes)[0]
            for subclass in textx_class._tx_inh_by
        )
        outdict['str'] = 'or', tuple(
            treated_classes[subclass]['name']
            for subclass in textx_class._tx_inh_by
        )
        outdict['doc'] = doc_from_class(textx_class)
    elif textx_class.__name__ in {'STRING', 'INT', 'FLOAT', 'ID', 'BOOL', 'NUMBER'}:
        outdict['type'] = textx_class
    else:
        outdict['children'] = []  # iterable of (name, structure)
        outdict['str'] = render_arpeggio_sequence(textx_class._tx_peg_rule)
        outdict['doc'] = doc_from_class(textx_class)


        # if name:
            # print('CLS:', name, textx_class)
        # else:
            # print('CLS:', textx_class)
        # print('\t', type(textx_class).__name__ == 'TextXMetaClass', textx_class.__name__)
        # print(dir(textx_class))
        # print_obj(textx_class)
        for name, obj in textx_class._tx_attrs.items():

            # target = obj
            # target = textx_class
            # target = textx_class._tx_peg_rule.nodes[0]
            target = textx_class._tx_peg_rule
            # if isinstance(target, arpeggio.Sequence):
                # for node in target.nodes:
                    # if isinstance(node, arpeggio.StrMatch):
                        # target = node
                        # print()
                        # print()
                        # print()
                        # print(target)
                        # print(type(target))
                        # print(dir(target))
                        # print_obj(target)
            outdict['children'].append((name, search_for_structure_info(obj, name=name, treated_classes=treated_classes)[0]))
    return outdict, treated_classes


CHARS_AS_READABLE = {
    None: 'any space, including line break',
    ',': 'comma',
    ';': 'semicolon',
    '\n': 'line break',
    ' ': 'space',
    '.': 'dot',
}


def str_sequence_doc(sequence:tuple) -> [str]:
    """Yield mkd lines describing given tuple sequence representing the grammar"""
    print('SEQUENCE:', sequence)
    while len(sequence) == 1:   sequence, = sequence
    type_, *data = sequence
    # print('        :', type_, data)
    if type_ == 'sequence':
        # handle the cases where MANY sequences are just chained without much information in it
        if len(data) == 1 and len(data[0]) == 1 and len(data[0][0]) == 2 and data[0][0][0] == 'sequence':
            yield from str_sequence_doc(data[0])
        else:
            print('SEQUENCE:', data)
            yield ''
            # prefix = ('' if len(data) == 1 else '- ') + 'Type '
            for gen in map(str_sequence_doc, data):
                yield 'Type ' + next(gen)
                for totype in gen:
                    if totype:
                        # print('TOTYPE:', '"' + totype + '"', gen)
                        yield ', then ' + totype
                # print()
    elif type_ == '0..*':
        assert len(data) == 2
        objname, sep = data
        sep = CHARS_AS_READABLE.get(sep, "\'" + str(sep) + "\'")
        yield f'zero or any number of [{objname}](#{objname.lower()}) separated by {sep}'
    elif type_ == '1..*':
        assert len(data) == 2
        objname, sep = data
        sep = CHARS_AS_READABLE.get(sep, "\'" + str(sep) + "\'")
        yield f'at least one [{objname}](#{objname.lower()}) separated by {sep}'
    elif type_ == '0..1':
        assert len(data) == 1
        objname, = data
        if isinstance(objname, tuple):
            yield f'Optionally (zero or one):'
            yield from ('    ' + line for line in str_sequence_doc(objname))
        else:
            yield f'optionally a [{objname}](#{objname.lower()})'
    elif type_ == 'or':
        assert len(data) == 1
        yield f'one of:'
        yield ''
        for objname in data[0]:
            yield f'- <a href="#{objname}">{objname}</a>'
    elif type_ == 'regex':
        assert len(data) == 1, data
        examples = tuple(get_match_examples(data[0]))
        yield 'anything matching the regex ' + render_regex(data[0], examples) + ' For example:'
        yield ''
        for example in examples:
            yield '    - "' + example + '"'
    elif type_ == 'special regex':
        assert len(data) == 1, data
        regex = SPECIAL_REGEXES[data[0].upper()]
        examples = tuple(get_match_examples(regex))
        regex_repr = render_regex(regex, examples)
        examples_repr = ', '.join(f'<b>{example}</b>' for example in examples)
        yield 'Anything corresponding to the ' + data[0].upper() + ' regex, for example ' + examples_repr + '.'
        yield 'The ' + data[0].upper() + ' regex is ' + regex_repr
    elif type_ == 'choice':
        while len(data) == 1: data, = data
        yield 'any one of the following: ' + ', '.join(line for datum in data for line in str_sequence_doc(datum))
    elif type_ is str:
        assert len(data) == 1 and isinstance(data[0], str), data
        yield data[0]
    elif isinstance(type_, tuple) and len(type_) == 2 and type_[0] is str:
        yield '`' + type_[1] + '`'
        yield from str_sequence_doc(data)
    elif isinstance(type_, tuple):
        yield from str_sequence_doc(type_)
        if isinstance(type_, tuple):
            yield from str_sequence_doc(data)
        else:
            yield data
    else:  # none of all that
        raise ValueError(f"Unhandled tostr sequence '{type_}', '{data}'")



def gen_doc(tree_model:dict, *, done_classes=set()) -> [str]:
    """Yield paragraph of mkd data

    TODO:
    - tooltips on class names and abstract rules: https://www.w3schools.com/howto/howto_css_tooltip.asp

    """
    # print(tree_model)
    if tree_model['name'] in done_classes:
        return  # nothing to write
    done_classes.add(tree_model['name'])
    yield f"# {tree_model['name']}"
    if 'regex' in tree_model:
        yield from str_sequence_doc(('regex', tree_model['regex'][1]))
    elif tree_model['name'] in SPECIAL_REGEXES:  # a base type
        yield from str_sequence_doc(('special regex', tree_model['name']))
    else:  # it's a regular rule
        yield from str_sequence_doc(tree_model['str'])
        if tree_model['doc']:  yield tree_model['doc']
        # handle children
        target = 'children' if 'children' in tree_model else 'choice'
        for child in tree_model.get(target):
            yield '\n\n<br/>\n\n'
            if isinstance(child, tuple) and isinstance(child[1], dict) and 'select' in child[1]:
                selection = child[1]['select']
                if len(selection) == 2 and isinstance(selection[1], dict):
                    child = selection[1]
            yield from gen_doc(child, done_classes=done_classes)




if __name__ == '__main__':
    tree_model, classes = search_for_structure_info(METAMODEL.rootcls)
    # print(tree_model)
    # pprint(tree_model)
    # for line in gen_doc(tree_model):
        # print(line)


    doc = '\n'.join(gen_doc(tree_model))
    import markdown
    with open('out.html', 'w') as fd:
        html = markdown.markdown(doc)
        # print(html)
        fd.write(html)


