"""Choo — UK train times CLI."""

import typer

from choo import __version__


app = typer.Typer(
    name="choo",
    help="UK train times from your terminal.",
    no_args_is_help=False,
    invoke_without_command=True,
)


def version_callback(value: bool):
    if value:
        typer.echo(f"choo {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", callback=version_callback, is_eager=True,
        help="Show version and exit.",
    ),
):
    """UK train times from your terminal."""
    pass
