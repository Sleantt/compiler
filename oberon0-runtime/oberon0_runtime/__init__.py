# SPDX-FileCopyrightText: 2025 Luca Michel <luca.michel@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon0 runtime for WASM module
"""

import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger
from pydantic import BaseModel, ConfigDict
from rich import print
from wasmtime import (
    Func,
    FuncType,
    Global,
    GlobalType,
    Instance,
    Limits,
    Memory,
    MemoryType,
    Module,
    Store,
    ValType,
)

INT32_SIZE = 4
INITIAL_STACK_POINTER = 1 << 16


class ReturnCode(Enum):
    SUCCESS = 0
    FILE_NOT_FOUND = 1
    COMMAND_NOT_FOUND = 2
    NO_MORE_INPUT = 3


app = typer.Typer()


class Context(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    store: None | Store
    buffer: list[int]
    memory: None | Memory


context = Context(buffer=[], store=None, memory=None)


# Runtime functions
def open_input():
    """open-input is a no-op for compatibility with the original Oberon0 runtime."""
    logger.debug("OpenInput()")


def read_int(address: int):
    """Reads an integer from the input buffer and store it in the memory
    at the given address."""
    logger.debug(f"ReadInt({address})")
    try:
        val = context.buffer.pop(0)
    except IndexError:
        print("[bold red]Error: no more input[/bold red]")
        raise typer.Exit(code=ReturnCode.NO_MORE_INPUT.value) from None

    context.memory.write(context.store, val.to_bytes(INT32_SIZE, "little"), address)


def eot_() -> int:
    """Check if there are still elements in the input buffer."""
    logger.debug("EOT()")
    return 1 if len(context.buffer) == 0 else 0


def write_char(c):
    """
    Write a character to the standard output.
    """
    logger.debug(f"WriteChar({c})")
    print(chr(c), end="")


def write_int(i, len):
    """Write an integer to the standard output using a width of `len` characters
    (padded with spaces).
    """
    logger.debug(f"WriteInt({i}, {len})")
    print(f"{i:{len}d}", end="")


def write_ln():
    """Write a newline character to the standard output."""
    print()


# Main function
@app.command()
def main(
    wasm_file: Annotated[Path, typer.Argument()],
    command: Annotated[str, typer.Argument()],
    numbers: Annotated[list[int] | None, typer.Argument()] = None,
    debug: bool = False,
):
    logger.remove()
    if debug:
        logger.add(sys.stdout, level="DEBUG")
    else:
        logger.add(sys.stdout, level="INFO")

    if numbers is not None:
        context.buffer.extend(numbers)

    context.store = Store()

    try:
        module = Module.from_file(context.store.engine, wasm_file)
    except FileNotFoundError:
        print(f"[bold red]Error: WASM file '{wasm_file}' not found[/bold red]")
        raise typer.Exit(code=ReturnCode.FILE_NOT_FOUND.value) from None

    f_open_input = Func(context.store, FuncType([], []), open_input)
    f_read_int = Func(context.store, FuncType([ValType.i32()], []), read_int)
    f_eot = Func(context.store, FuncType([], [ValType.i32()]), eot_)
    f_write_char = Func(context.store, FuncType([ValType.i32()], []), write_char)
    f_write_int = Func(
        context.store, FuncType([ValType.i32(), ValType.i32()], []), write_int
    )
    f_write_ln = Func(context.store, FuncType([], []), write_ln)

    context.memory = Memory(context.store, MemoryType(Limits(1, None)))
    sp = Global(
        context.store, GlobalType(ValType.i32(), mutable=True), INITIAL_STACK_POINTER
    )

    instance = Instance(
        context.store,
        module,
        [
            f_open_input,
            f_read_int,
            f_eot,
            f_write_char,
            f_write_int,
            f_write_ln,
            context.memory,
            sp,
        ],
    )

    try:
        cmd = instance.exports(context.store)[command]
    except KeyError:
        print(f"[bold red]Error: command '{command}' not found[/bold red]")
        raise typer.Exit(code=ReturnCode.COMMAND_NOT_FOUND.value) from None
    cmd(context.store)


if __name__ == "__main__":
    app()
