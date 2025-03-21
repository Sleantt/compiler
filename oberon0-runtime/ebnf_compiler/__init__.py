# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
EBNF Compiler
"""
import sys
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty

import ebnf_compiler.stat
from ebnf_compiler.parser import Parser
from ebnf_compiler.scanner import Scanner

console = Console()
app = typer.Typer()


@app.command(context_settings={"ignore_unknown_options": True})
def main(
    source: Annotated[Path, typer.Argument()],
    debug: bool = False,
    show_tree: bool = False,
    stats: bool = False,
):

    logger.remove()
    if debug:
        logger.add(sys.stdout, level="DEBUG")
    else:
        logger.add(sys.stdout, level="INFO")

    scanner = Scanner()
    scanner.open(source)
    parser = Parser(scanner=scanner)

    try:
        ast = parser.parse()
    except SyntaxError as e:
        print(f"{e.msg} (File {e.filename}, Line {e.lineno}, Column {e.offset})")

    if parser.has_error:
        print("Syntax errors. aborting")
        raise typer.Exit(code=1)

    if show_tree:
        console.print(Panel(Pretty(ast, indent_size=2), title="Syntax Tree"))
    else:
        console.print(Panel(str(ast), title="Code"))

    if stats:
        non_terminals, terminals = ebnf_compiler.stat.symbols(ast)

        nts = [i for i in sorted(list(non_terminals))]
        console.print(Panel("\n".join(nts), title="Non-terminal Symbols"))

        ts = [f"`{i}`" for i in sorted(list(terminals))]
        console.print(
            Panel(Columns(ts, equal=True, expand=True), title="Terminal Symbols")
        )


if __name__ == "__main__":
    app()
