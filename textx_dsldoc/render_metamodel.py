"""Routines to render a metamodel.

"""

import textx
import arpeggio
import markdown
from .render_utils import print_obj, get_match_examples, doc_from_class, render_regex, as_regex, SPECIAL_REGEXES, str_sequence_doc, render_arpeggio_sequence, CHARS_AS_READABLE
from .render_arpeggio import render_arpeggio_sequence_as_str


class ParsingSequence:

    def __init__(self, peg_rule):
        self.sequence = render_arpeggio_sequence(peg_rule)
        self.sequence_repr = tuple(render_arpeggio_sequence_as_str(peg_rule))

    def as_markdown(self):
        """Yield mkd lines describing self sequence tuple representing the grammar"""
        yield ''
        yield '<p style="margin-left: 40px"><tt>' + markdown.markdown(' '.join(self.sequence_repr)) + '</tt></p>'
        yield ''
        to_add = []
        for item in self.sequence:
            type_line, *sublines = ParsingSequence.item_repr(item)
            if type_line:
                # print('LINER:', type_line, f'\t({len(sublines)} sublines)')
                yield '- Type ' + type_line
            for line in sublines:
                head = '    ' if line.startswith(' ') else '    - '
                yield head + line

    @staticmethod
    def item_repr(item) -> [str]:
        while len(item) == 1: item, = item
        if not item:
            pass  # nothing to do
        elif item[0] == 'regex':
            yield f'anything matching regex {render_regex(item[1])}'
        elif item[0] == 'special regex':
            yield f'anything matching standard regex {item[1].upper()}'
        elif len(item) == 3 and item[0] in {'0..*', '1..*'}:
            _, objname, sep = item
            sep = CHARS_AS_READABLE.get(sep, "\'" + str(sep) + "\'")
            if item[0] == '0..*':
                yield f'zero or any number of [{objname}](#{objname.lower()}) separated by {sep}'
            else:
                yield f'at least one [{objname}](#{objname.lower()}) separated by {sep}'
        elif len(item) == 2 and item[0] == '0..1':
            _, sub = item
            while len(sub) == 1: sub, = sub
            first, *lasts = ParsingSequence.item_repr(sub)
            yield f'optionally ' + first
            yield from lasts
        elif len(item) == 2 and item[0] is str:
            yield f'the string `{item[1]}`'
        elif item[0] == 'choice':
            # In order to avoid a sublist, the following machinery avoid having
            #  a sublist when there is few elements, all described by a single line.
            assert len(item) == 2
            lines = []
            inline = len(item[1]) < 4  # if True, push the content in a single line
            # NOTE: be based on the final length instead of the number of item would be more robust.
            for sub in item[1]:
                first, *nexts = ParsingSequence.item_repr(sub)
                lines.append(first)
                for next_ in nexts:
                    lines.append('    - ' + next_)
                    inline = False  # we can't put it into a single line
            if inline:
                yield 'either ' + ' or '.join(lines)
            else:  # multiple lines
                yield 'one of the following:'
                yield from lines
        elif isinstance(item, tuple):  # this is a composed object
            yield 'in this order:'
            for sub in item:
                yield from ParsingSequence.item_repr(sub)
        else:  # Unexpected object
            print('WOOT:', item)
            yield item


class DocSection:
    """

    TODO:
    - tooltips on class names and abstract rules: https://www.w3schools.com/howto/howto_css_tooltip.asp

    """

    def __init__(self, name:str, names_in_parents:set=set(), raw_doc:str='', sequence:tuple=()):
        self.name = str(name)
        self.names_in_parents = frozenset(names_in_parents)
        self.raw_doc = str(raw_doc or '')
        self.sequence = ParsingSequence(sequence) if sequence else None

    def as_markdown(self):
        yield '# ' + self.name
        if self.raw_doc:
            yield self.raw_doc
        if self.sequence:
            yield ''
            yield from self.sequence.as_markdown()

    def as_html(self) -> str:
        return markdown.markdown('\n'.join(self.as_markdown()))

    @staticmethod
    def from_textx_class(textx_class) -> (str, object):
        """Build and return an instance from given textx class"""
        cls, kwargs = DocSection, {'names_in_parents': set(), 'raw_doc': doc_from_class(textx_class)}
        if hasattr(textx_class, '__name__'):
            kwargs['name'] = textx_class.__name__
        # print_obj(textx_class)
        assert hasattr(textx_class, '__name__'), textx_class
        if not hasattr(textx_class, '_tx_attrs'):
            return
        regex = as_regex(textx_class)
        if regex:
            cls = DocRegexSection
            kwargs['regex'] = regex
        elif textx_class.__name__ in SPECIAL_REGEXES:
            return textx_class.__name__  # don't need more, since these are autogenerated in another way
        elif isinstance(textx_class, textx.metamodel.MetaAttr):  # it's a ?=, += or *=
            cls = DocSelectionSection
            kwargs['selection'], kwargs['target'] = textx_class.mult, textx_class.cls
        elif not textx_class._tx_attrs and textx_class._tx_inh_by:  # it's a raw choice
            cls = DocChoiceSection
            kwargs['choice'] = tuple(textx_class._tx_inh_by)
        else:  # it's a "regular" rule
            kwargs['sequence'] = textx_class._tx_peg_rule
        return cls(**kwargs)


class DocChoiceSection(DocSection):
    def __init__(self, choices:tuple, **kwargs):
        self.choices = tuple(choices)
        super().__init__(**kwargs)

    def as_markdown(self):
        yield from super().as_markdown()
        yield ''
        for choice in self.choices:
            yield '- ' + str(choice)

class DocSelectionSection(DocSection):
    def __init__(self, selection:str, target:object, **kwargs):
        self.target = str(target)
        self.selection = str(selection)
        super().__init__(**kwargs)

    def as_markdown(self):
        yield from super().as_markdown()
        yield ''
        print('SELECTION:', self.target)
        if self.selection == '0..1':
            yield 'Optionally, type a ' + str(self.target)
        elif self.selection == '1..*':
            yield 'Type at least one ' + str(self.target)
        elif self.selection == '0..*':
            yield 'Type zero or any number of ' + str(self.target)

class DocRegexSection(DocSection):
    def __init__(self, regex:str, **kwargs):
        self.regex = str(regex)
        super().__init__(**kwargs)

    def as_markdown(self):
        yield from super().as_markdown()
        examples = get_match_examples(self.regex, amount=4)
        render = render_regex(self.regex, get_match_examples(self.regex, amount=0))
        yield f'{self.name.title()} is a *regex rule*, detecting anything matched by {render}, such as:'
        yield ''
        for example in examples:
            yield f'- <pre>{example}</pre>'
        yield ''


if __name__ == '__main__':
    classes = [METAMODEL.rootcls] + list(METAMODEL.user_classes.values())
    print('CLASSES:', classes)
    with open('out.html', 'w') as fd:
        for cls in classes:
            out = DocSection.from_textx_class(cls)
            if out:
                fd.write(out.as_html())
                fd.write('<br/><br/>\n')
