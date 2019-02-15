"""Definition of the objects needed to handle the DSL.

Wildly taken from https://github.com/Aluriak/24h2019

"""

import math
import time
import textx
import random
import operator
import itertools
from pprint import pprint

SPATIAL_POSITION = {
    'LaumioA': 0,
    'LaumioB': 1,
    'LaumioC': 2,
    0: 'LaumioA',
    1: 'LaumioB',
    2: 'LaumioC',
}

GRAMMAR = """

DSL:
    commands*=BaseCommand;
BaseCommand:
    (Require | Group | Color | Condition | Callback | Runfile | Wait) '.'?;
//    (Runfile | Group) '.'?;


Require:
    'require' sensor=Identifier;

Group:
    'group' laumios+=Identifier[','] 'as' groupname=Identifier;

Color:
    ('fill' | 'color') group_or_laumio+=Identifier[','] (specifier=Identifier (target='ring' | target='column'))? ('in' | 'as') color=Identifier;

Condition:
    'if' comparison=Comparison '{' ifcommands*=BaseCommand '}' 'else' '{' elsecommands*=BaseCommand '}';

Callback:
    'whenever' comparison=Comparison '{' subcommands*=BaseCommand '}';

Runfile:
    ('run'|'runfile') filename+=Filename[','];

Wait:
    'wait' ((amount=FLOAT unit=Unit) | amount='forever');


//#####################


Comparison:
    SensorComparison | ButtonComparison;
SensorComparison:
    sensor=Identifier op=Operator cmp_value=ComparableValue;
ButtonComparison:
    'button' button_number=INT 'is' negation?='not' 'pressed';


//#####################
ComparableValue:
    INT | FLOAT | Identifier;
Operator:
    op=/==|>=|<=|!=|=\/=|=|>|</;
Identifier:  id=/[a-zA-Z0-9_-]+/;
Filename:    id=/[a-zA-Z0-9\.\/\~\[\]\\'"_-]+/;
Unit:        id=/(s|second|seconds|m|min|hour|h|day|d)/;
"""

class Laumio:
    def __init__(self, name):
        self.name = name
        self.print = lambda *a, **k: None
        self.print = print
    def top_ring(self, color):
        self.print('COLOR TOP WITH:', color)
    def middle_ring(self, color):
        self.print('COLOR MIDDLE WITH:', color)
    def bottom_ring(self, color):
        self.print('COLOR BOTTOM WITH:', color)
    def color_wipe(self, duration, color):
        self.print('COLOR BOTTOM WITH:', duration, color)
    def set_ring(self, *args):
        print('SET RING:', args)
    def set_column(self, *args):
        print('SET COLN:', args)
    def get_bp_button_status(self, numButton):
        """return boolean"""
        return random.choice((True, False))
    def fill(self, color):
        print('FILL:', color)

    @staticmethod
    def init_all(*args, **kwargs):
        for name_or_id in SPATIAL_POSITION:
            if isinstance(name_or_id, str):  # it's a name
                yield Laumio(name_or_id)

ENUMERATION_WORDS = {
    '1': 2,
    'top': 2,
    'first': 2,
    '2': 1,
    'middle': 1,
    'second': 1,
    '3': 0,
    'last': 0,
    'third': 0,
    'bottom': 0,
}
OPERATOR_FUNC = {
    '==': operator.eq,
    '<=': operator.le,
    '>=': operator.ge,
    '<': operator.lt,
    '>': operator.gt,
    '!=': operator.ne,
    '=/=': operator.ne,
}


def laumio_from_name_or_id(id_or_name:str or int, context={}):
    # print(f'LAUMIO FROM {id_or_name} in {SPATIAL_POSITION}')
    if id_or_name.isnumeric():
        id_or_name = int(id_or_name)
    if isinstance(id_or_name, int):
        id_or_name = SPATIAL_POSITION[id_or_name]
    assert isinstance(id_or_name, str)
    for laumio in context['laumios']:
        # print('\tPROPOSITION:', laumio.name, id_or_name)
        if laumio.name == id_or_name:
            return laumio


# classes used to build the raw model

def model_class(name: str, bases: tuple, attrs: dict) -> type:
    """Metaclass to automatically build the __init__ to get the properties,
    and register the class for metamodel
    """
    if "__init__" not in attrs:

        def __init__(self, *args, **kwargs):
            for field, value in kwargs.items():
                setattr(self, field, value)

        attrs["__init__"] = __init__
    cls = type(name, bases, attrs)
    model_class.classes.append(cls)
    return cls

model_class.classes = []


class Require(metaclass=model_class):
    def execute(self, context, callbacks):
        self.context.setdefault('require', set()).add(self.sensor)

class Group(metaclass=model_class):
    def execute(self, context, callbacks):
        laumios = tuple(map(context['get laumio'], (l.id for l in self.laumios)))
        self.groupname = self.groupname.id
        print(f'CREATE GROUP {self.groupname}: {laumios}')
        for laumio in laumios:
            if laumio is None:
                print("WARNING: a laumio wasn't found")
        context['groups'][self.groupname] = tuple(l for l in laumios if l)

class Color(metaclass=model_class):
    def execute(self, context, callbacks):
        laumios = []
        for group_or_laumio in self.group_or_laumio:
            real_name = group_or_laumio.id
            if isinstance(real_name, str) and real_name in context['groups']:
                laumios.extend(context['groups'][real_name])
            else:  # it's a single laumio that is targeted
        # print('GROUP OR LAUMIO:', real_name)
                laumios.append(context['get laumio'](real_name))
        print('COLLECTED LAUMIO:', laumios)
        if self.target == 'ring':
            self.specifier = ENUMERATION_WORDS.get(self.specifier.lower(), self.specifier).lower()
            for laumio in laumios:
                laumio.set_ring(self.specifier, self.color.id)
        elif self.target == 'column':
            self.specifier = ENUMERATION_WORDS.get(self.specifier.lower(), self.specifier)
            for laumio in laumios:
                laumio.set_column(self.specifier, self.color.id)
        elif not self.target:
            for laumio in laumios:
                laumio.fill(self.color.id)
        else:
            raise DSLSyntaxError(f"Invalid target '{self.target}' for color command.")



class Callback(metaclass=model_class):
    def execute(self, context, callbacks):
        callbacks.append((self.comparison.caller, self.subcommands))

class Condition(metaclass=model_class):
    def execute(self, context, callbacks):
        if self.comparison.caller(context, callbacks)():
            for command in self.ifcommands:
                command.execute(context, callbacks)
        else:
            for command in self.elsecommands:
                command.execute(context, callbacks)

class SensorComparison(metaclass=model_class):
    def caller(self, context, callbacks) -> callable:
        def verify_condition() -> bool:
            if self.sensor == 'temperature':
                value = float(context['laumios'][0].atmos.temperature)
            if self.sensor == 'pressure':
                value = float(context['laumios'][0].atmos.pression)
            if self.sensor == 'humidity':
                value = float(context['laumios'][0].atmos.humidity)
            if self.sensor == 'abs_humidity':
                value = float(context['laumios'][0].atmos.humidity_abs)
            print('VERIFY:', OPERATOR_FUNC[self.op.op], value, self.cmp_value, '-->', OPERATOR_FUNC[self.op.op](value, self.cmp_value))
            return OPERATOR_FUNC[self.op.op](value, self.cmp_value)
        return verify_condition
class ButtonComparison(metaclass=model_class):
    def caller(self, context, callbacks) -> callable:
        def verify_condition() -> bool:
            pressed = context['laumios'][0].get_bp_button_status(int(self.button_number))
            return (not pressed) if self.negation else pressed
        return verify_condition

class Wait(metaclass=model_class):
    def execute(self, context, callbacks):
        if self.amount == 'forever':
            assert self.unit is None
            ttw = math.inf
        else:
            assert self.amount is not None
            assert self.unit is not None
            multiplier = {
                'h': 3600,
                'hour': 3600,
                'hours': 3600,
                'minutes': 60,
                'minute': 60,
                'm': 60,
            }
            assert isinstance(self.unit, str)
            assert isinstance(self.amount, float)
            ttw = multiplier.get(self.unit, 1) * self.amount
        while ttw > 0:
            context['call callbacks'](context, callbacks)
            time.sleep(1)
            ttw -= 1


class Runfile(metaclass=model_class):
    def execute(self, context, callbacks):
        interpret_string(self.filename.value, context=context, callbacks=callbacks)

class Filename(metaclass=model_class):
    @property
    def value(self):
        return self.id
class Identifier(metaclass=model_class):
    @property
    def value(self):
        return self.id


print(model_class.classes)
METAMODEL = textx.metamodel_from_str(
    GRAMMAR, classes=model_class.classes, debug=False
)


class DSLSyntaxError(ValueError):
    pass


def interpret_string(raw_code: str, *, context:dict={}, callbacks:list=[]) -> dict:
    if not context:
        context['groups'] = {}  # group name: laumios in the group
        context['laumios'] = tuple(Laumio.init_all('mpd.lan'))
        # context['laumios'] = Laumio.init_all()
        context['get laumio'] = lambda *a, **k: laumio_from_name_or_id(*a, **k, context=context)
        def call_callbacks(context, callbacks):
            print('calling callbacks…')
            for condition, subcommands in callbacks:
                if condition(context, callbacks)():
                    for command in subcommands:
                        command.execute(context, callbacks)
        context['call callbacks'] = call_callbacks
    try:
        raw_model = METAMODEL.model_from_str(raw_code)
    except textx.exceptions.TextXSyntaxError as err:
        raise DSLSyntaxError(*error_message_from_err(err, raw_code))
    for command in raw_model.commands:
        command.execute(context, callbacks)
        # print('CALLBACKS:', callbacks)
        context['call callbacks'](context, callbacks)


def error_message_from_err(
    err: textx.exceptions.TextXSyntaxError, raw_vql: str
) -> (str, int):
    """Return human-readable information and index in raw_sql query
    about the given exception"""
    # print(err)
    # print(dir(err))
    # print(err.args)
    # print(err.err_type)
    # print(err.line, err.col)
    # print(err.message)
    # print(err.filename)
    # print(err.expected_rules)
    if "'SELECT'" in err.message:  # was awaiting for a SELECT clause
        return "no SELECT clause", -1
    if err.message.endswith("=> 's,ref FROM*'."):
        return "empty 'FROM' clause", err.col
    if (
        ",*," in err.message
        and len(err.expected_rules) == 1
        and type(err.expected_rules[0]).__name__ == "RegExMatch"
    ):
        return "invalid empty identifier in SELECT clause", err.col
    if (
        "Expected INT " in err.message
        and len(err.expected_rules) == 3
    ):
        return "invalid value in WHERE clause", err.col
    if (
        "Expected '==|>=|<=|!=" in err.message
        and len(err.expected_rules) == 1
    ):
        return "invalid operator in WHERE clause", err.col

    raise err  # error not handled. Just raise it




if __name__ == '__main__':
    print(interpret_string("""

    group 1, 2 as g1.
    group 0, 1 as g2.

    fill g1 in red.

    whenever button 1 is pressed {
        color g2 in green
    }
    whenever button 1 is not pressed {
        color g2 in red
    }

    wait forever.


    """))

