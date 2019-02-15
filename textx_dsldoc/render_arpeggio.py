"""Routines for the rendering of an Arpeggio grammar.
"""

import arpeggio
from .render_utils import print_obj, render_regex, SPECIAL_REGEXES, SPECIAL_REGEXES_REV


REPEAT_TO_STR = {
    arpeggio.Optional: '?',
    arpeggio.ZeroOrMore: '*',
    arpeggio.OneOrMore: '+',
}


def render_arpeggio_sequence_as_str(peg_rule) -> [str]:
    """Render arpeggio sequence of given class until reaching terminals or textx classes"""

    # print_obj(peg_rule)
    for item in peg_rule.nodes:
        if isinstance(item, arpeggio.StrMatch):
            yield item.to_match
        elif isinstance(item, (arpeggio.Optional, arpeggio.ZeroOrMore, arpeggio.OneOrMore)):
            # print(f'{type(item)}:', item)
            # print_obj(item)
            assert len(item.nodes) == 1
            sep = f'[{item.sep}]' if item.sep else ''
            if hasattr(item.nodes[0], '_tx_class'):  # it's applied on a known object
                cls = item.nodes[0]._tx_class.__name__
                cls = f'[{cls}](#{cls.lower()})'
                yield f'{getattr(item, "_attr_name", "")}{REPEAT_TO_STR[type(item)]}={cls}{sep}'
            else:  # it's more complicated than that
                subrepr = ' '.join(render_arpeggio_sequence_as_str(item.nodes[0]))
                yield f'{getattr(item, "_attr_name", "")}{REPEAT_TO_STR[type(item)]}={subrepr}{sep}'
        elif isinstance(item, arpeggio.RegExMatch):
            if item.to_match in SPECIAL_REGEXES_REV:
                name = SPECIAL_REGEXES_REV[item.to_match]
                yield f'[{name}](#{name.lower()})'
            else:
                yield render_regex(item.to_match)
        elif isinstance(item, arpeggio.OrderedChoice):
            yield '(' + '|'.join(render_arpeggio_sequence_as_str(item)) + ')'
        elif isinstance(item, arpeggio.Sequence):
            # print_obj(item)
            yield '  '.join(render_arpeggio_sequence_as_str(item))
        else:  # probably an arpeggio.Sequence that wasn't handled previously
            print_obj(item)
            raise ValueError(f"Unexpected arpeggio node '{item}' of type {type(item)}")


if __name__ == "__main__":
    from example import METAMODEL
    for cls in METAMODEL.user_classes.values():
        print(cls.__name__ + ':', '\n- ' + '\n- '.join(render_arpeggio_sequence_as_str(cls._tx_peg_rule)))

