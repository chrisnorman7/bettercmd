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
    cmd = c.command(print)
    assert isinstance(cmd, BetterCmdCommand)
    assert cmd.parser is None


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

    @c.command
    @c.alias('quit')
    def bye(self, args):
        print('Quitting.')

    b = c.commands['bye']
    assert isinstance(b, BetterCmdCommand)
    assert b is c.commands['quit']
    assert c.commands == {'quit': b, 'bye': b}


def test_alias_without_func_name():
    c = BetterCmd()

    @c.command
    @c.alias('quit', add_function=False)
    def bye(self, args):
        print('Quitting.')

    q = c.commands['quit']
    assert isinstance(q, BetterCmdCommand)
    assert c.commands == {'quit': q}


def test_option():
    filename = 'test.file'
    c = BetterCmd()

    @c.command
    @c.option('-f', '--file', help='Filename')
    def open(self, args):
        assert args.file == filename
        raise CommandWorks()

    with raises(CommandWorks):
        args = f'-f {filename}'
        c.commands['open'](args, args.split())


def test_option_multiple():
    host = '127.0.0.1'
    port = 80
    c = BetterCmd()

    @c.command
    @c.option('host', default=host, help='Hostname')
    @c.option('port', type=int, default=port, help='Port')
    def connect(self, args):
        assert args.port == port
        assert args.host == host
        raise CommandWorks()

    args = f'{host} {port}'
    with raises(CommandWorks):
        c.commands['connect'](args, args.split())
