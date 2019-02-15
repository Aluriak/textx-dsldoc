"""Introduce DSLDoc as a textx subcommand.

"""

import os
import click
import textx
from .converters import markdown_from_metamodel, html_from_metamodel

@click.argument('target', type=click.Path(exists=True, dir_okay=False, readable=True))
                # filename for a grammar in TextX format, or a python file defining a metamodel
@click.option('-m', '--metamodel', type=str, default='metamodel',
              help='if target is a python file, name of the variable accessing the metamodel')
@click.option('-i', '--import-target', type=bool, default=False,
              help='if target is a python file, use importlib to retrieve internal states')
@click.option('-o', '--output', default='out.html',
              type=click.Path(dir_okay=False, writable=True),
              help='directory to populate with resulting HTML or markdown, depending of the extension')
def autodoc(target:str, metamodel:str, import_target:bool, output:str):
    """Subcommand added to textx. Will search for given grammar or metamodel,
    and generate its doc.

    """
    click.echo(f"\n\nBEGINNING…")
    click.echo(f"{target}\t\t{metamodel}")
    if os.path.splitext(target)[1] == '.py':
        if import_target:
            module = importlib.import_module(target)
            metamodel = getattr(module, var_metamodel)
        else:  # use the good old exec()
            with open(target) as fd:
                pycode = fd.read()
            globals = {}
            exec(pycode, globals)
            metamodel = globals[metamodel]
        click.echo(f"Found a metamodel in target")
    else:  # let's hope it's a grammar
        click.echo(f"Found a grammar in target")
        metamodel = textx.metamodel_from_file(target)
    click.echo("Generating documentation…")
    click.echo(output)
    converter = html_from_metamodel if os.path.splitext(output)[1] in {'.htm', '.html'} else markdown_from_metamodel
    with open(output, 'w') as fd:
        fd.write(converter(metamodel))
