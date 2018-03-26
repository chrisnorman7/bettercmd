"""A better cmd.py."""

import os
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, Namespace
from inspect import getdoc
from shlex import split
from attr import attrs, attrib, Factory
from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory


__all__ = [
    'BetterCmdError', 'DuplicateNameError', 'CommandExit',
    'BetterCmdArgumentParser', 'BetterCmdCommand', 'BetterCmd'
]


class BetterCmdError(Exception):
    """Base error."""


class DuplicateNameError(BetterCmdError):
    """There is already a command by this name."""


class CommandExit(BetterCmdError):
    """A command exited for some reason."""


class BetterCmdArgumentParser(ArgumentParser):
    """Overwrite stupid methods."""

    def __init__(self, *args, **kwargs):
        self.command = None
        super().__init__(*args, **kwargs)

    def _print_message(self, message, file=None):
        """Print a message. If no file is provided use the stdout of the
        underlying command object."""
        if file is None:
            file = self.command.parent.stdout
        file.write(message)

    def exit(self, status=0, message=None):
        """Don't exit the program."""
        if message:
            self._print_message(message)
        raise CommandExit()


@attrs
class BetterCmdCommand:
    """A command that can be called from within the main loop."""

    parent = attrib()
    func = attrib()
    parser = attrib()

    def __call__(self, args_string, args_list):
        """Call self.func."""
        args = Namespace(args_string=args_string, args_list=args_list)
        if self.parser is not None:
            args = self.parser.parse_args(args=args_list, namespace=args)
        return self.func(self.parent, args)


@attrs
class BetterCmd:
    """Contains all the commands that can be called as well as the run function
    which starts the main loop. Decorate functions with the command decorator
    and add aliases with the alias decorator."""

    stdout = attrib(default=Factory(lambda: sys.stdout))
    stderr = attrib(default=Factory(lambda: sys.stderr))
    commands = attrib(default=Factory(dict))
    command_class = attrib(default=Factory(lambda: BetterCmdCommand))
    parser_class = attrib(default=Factory(lambda: BetterCmdArgumentParser))
    running = attrib(default=Factory(bool))
    prompt_message = attrib(default=Factory(lambda: '>'))
    prompt_history = attrib(default=Factory(InMemoryHistory))
    _all_aliases = attrib(default=Factory(set), init=False, repr=False)
    _aliases = attrib(default=Factory(dict), init=False, repr=False)
    _parsers = attrib(default=Factory(dict), init=False, repr=False)

    def print_message(self, message):
        self.stdout.write(message)
        self.stdout.write(os.linesep)
        self.stdout.flush()

    def create_parser(self):
        """Returns a parser to be used by the command decorator."""
        return self.parser_class(formatter_class=ArgumentDefaultsHelpFormatter)

    def split(self, line):
        """Returns line split into a list."""
        try:
            return split(line)
        except ValueError:
            return line.split()

    def command(self, func):
        """Decorate a function with this decorator to add it to the commands
        dictionary."""
        aliases = self._aliases.get(func, [func.__name__])
        cmd = self.command_class(self, func, self._parsers.get(func, None))
        if cmd.parser is not None:
            cmd.parser.command = cmd
            cmd.parser.prog = aliases[0]
            cmd.parser.description = getdoc(func)
        for name in aliases:
            self.commands[name] = cmd
        return cmd

    def alias(self, *names, add_function=True):
        """Add aliases for a command.
        Should be used after the command decorator. EG:
        @cmd.command
        @cmd.alias('quit')
        def bye(self, args):
            '''Exit the program.'''
            self.print_message('Goodbye.')
            self.running = False

        If add_function evaluates to True then the name of the function will be
        set as the first name in the list."""
        names = list(names)

        def inner(func):
            if add_function:
                names.insert(0, func.__name__)
            duplicates = self._all_aliases.intersection(names)
            if duplicates:
                raise DuplicateNameError(duplicates)
            aliases = self._aliases.get(func, [])
            aliases.extend(names)
            self._all_aliases.update(names)
            self._aliases[func] = aliases
            return func
        return inner

    def option(self, *args, **kwargs):
        """This decorator should be used after the command decorator. EG:
        @c.command
        @c.option('host', default='127.0.0.1', help='Hostname')
        @c.option('port', type=int, default=80, help='Port')
        def connect(self, args):
            '''Connect to somewhere.'''
            self.print_message(f'Connecting to {args.host}:args.port}.')

        Must be called as:
        command <host> <port>
        """
        def inner(func):
            if func not in self._parsers:
                self._parsers[func] = self.create_parser()
            parser = self._parsers[func]
            action = parser.add_argument(*args, **kwargs)
            if len(parser._actions) >= 3:
                # Shuffle arguments to ensure they're in the expected order:
                parser._actions.remove(action)
                parser._actions.insert(1, action)
            return func
        return inner

    def before_command(self, line):
        """Hook method executed just before the command line is interpreted,
        but after the input prompt is generated and issued. Can be used to
        modify the entered command."""
        return line

    def after_command(self, command):
        """Called after command was run. If nothing was entered at the command
        prompt or the command was unrecognised then command will be None."""

    def after_loop(self):
        """Called when the main loop exits."""

    def empty_command(self):
        """Nothing was entered at the command prompt."""

    def default(self, command, args_string, args_list):
        """Called when the entered command doesn't match any of the commands
        registered with the command decorator. The provided command is the
        command the user tried to enter, args_string is the arguments they
        supplied as a string, and args_list is the arguments they supplied as a
        list."""
        self.print_message(f'Unrecognised command: {command}.')

    def get_prompt(self):
        """Build a sensible prompt."""
        return prompt(message=self.prompt_message, history=self.prompt_history)

    def feed(self, command):
        """Feed the parser with a single command."""
        if not command:
            cmd = None
            self.empty_command()
        else:
            parts = self.split(command)
            command_name = parts[0]
            args_string = command[len(command_name) + 1:]
            args_list = parts[1:]
            cmd = self.commands.get(command_name, None)
            if cmd is None:
                self.default(command_name, args_string, args_list)
            else:
                try:
                    cmd(args_string, args_list)
                except CommandExit:
                    pass  # That's OK.
        return cmd

    def run(self):
        """Start the mainloop."""
        self.running = True
        while self.running:
            command = self.get_prompt()
            command = self.before_command(command)
            cmd = self.feed(command)
            self.after_command(cmd)
