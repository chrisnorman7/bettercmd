"""A better cmd.py."""

import os
import sys
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter, Namespace
from inspect import getdoc
from shlex import split
from attr import attrs, attrib, Factory
from prompt_toolkit import prompt
from prompt_toolkit.history import InMemoryHistory


class CommandExit(Exception):
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
    parser = attrib(default=Factory(lambda: None))

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
    running = attrib(default=Factory(bool))
    prompt_message = attrib(default=Factory(lambda: '>'))
    prompt_history = attrib(default=Factory(InMemoryHistory))

    def print_message(self, message):
        self.stdout.write(message)
        self.stdout.write(os.linesep)
        self.stdout.flush()

    def create_parser(self, command):
        """Given a command, returns a parser to be used by the command
        decorator."""
        return self.parser_class(
            command, prog=command.func.__name__,
            formatter_class=ArgumentDefaultsHelpFormatter,
            description=getdoc(command.func)
        )

    def split(self, line):
        """Returns line split into a list."""
        try:
            return split(line)
        except ValueError:
            return line.split()

    def command(self, func):
        """Decorate a function with this decorator to add it to the commands
        dictionary."""
        cmd = self.command_class(self, func)
        self.commands[func.__name__] = cmd
        return cmd

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
                cmd(args_string, args_list)
        return cmd

    def run(self):
        """Start the mainloop."""
        self.running = True
        while self.running:
            command = self.get_prompt()
            command = self.before_command(command)
            cmd = self.feed(command)
            self.after_command(cmd)
