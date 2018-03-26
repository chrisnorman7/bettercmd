from pytest import raises
from bettercmd import BetterCmd, BetterCmdCommand


class CommandWorks(Exception):
    pass


class Default(Exception):
    pass


class Empty(Exception):
    pass


class CustomBetterCmd(BetterCmd):
    def default(self, command, args_string, args_list):
        assert command == 'test'
        assert args_string == 'this out'
        assert args_list == ['this', 'out']
        raise Default()

    def empty_command(self):
        raise Empty()


cbc = CustomBetterCmd()


@cbc.command
def hello(self, args):
    assert args.args_string == 'cruel world'
    assert args.args_list == ['cruel', 'world']
    raise CommandWorks()


def test_command():
    c = BetterCmd()
    assert isinstance(c.command(print), BetterCmdCommand)


def test_default():
    with raises(Default):
        cbc.feed('test this out')


def test_empty():
    with raises(Empty):
        cbc.feed('')


def test_command_works():
    with raises(CommandWorks):
        cbc.feed('hello cruel world')


def test_alias():
    c = BetterCmd()

    @c.alias('quit')
    @c.command
    def bye(self, args):
        print('Quitting.')

    b = c.commands['bye']
    assert isinstance(b, BetterCmdCommand)
    assert b is c.commands['quit']
    assert c.commands == {'quit': b, 'bye': b}
