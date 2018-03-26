from bettercmd import BetterCmd

cmd = BetterCmd()


@cmd.command
def quit(self, args):
    """Quit the program."""
    self.running = False
    self.print_message('Goodbye.')


@cmd.command
def echo(self, args):
    """Echo back some text."""
    self.print_message(args.args_string)


@cmd.command
@cmd.option('host', help='The host to connect to')
@cmd.option('port', type=int, default=80, help='The port to connect to')
def connect(self, args):
    """Connect to something."""
    self.print_message(f'Conecting to {args.host}:{args.port}...')


if __name__ == '__main__':
    cmd.run()
