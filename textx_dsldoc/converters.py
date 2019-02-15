"""Definitions of high-level converters/compilers.

"""

import markdown
from .render_metamodel import DocSection


def markdown_from_metamodel(metamodel) -> str:
    """Return string containing markdown describing the auto-generated documentation
    of given metamodel."""
    return '\n'.join(gen_lines(metamodel))


def html_from_metamodel(metamodel) -> str:
    """Return string containing html describing the auto-generated documentation
    of given metamodel."""
    return markdown.markdown(markdown_from_metamodel(metamodel))


def gen_lines(metamodel) -> [str]:
    "Yield lines of markdown describing classes found in given metamodel"
    classes = [metamodel.rootcls] + list(metamodel.user_classes.values())
    print('CLASSES:', classes)
    for cls in classes:
        out = DocSection.from_textx_class(cls)
        if out:
            yield from out.as_markdown()
