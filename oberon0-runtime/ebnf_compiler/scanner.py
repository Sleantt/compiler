# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
EBNF Scanner
"""

import typing
from pathlib import Path

import typer
from loguru import logger
from pydantic import BaseModel
from rich import print

from ebnf_compiler.tokens import Token


class Scanner(BaseModel):
    eof: bool = False
    sym: Token | None = None  # Next Symbol
    value: str = ""

    _ch: str = ""
    _file_name: Path | None = None
    _text: typing.TextIO | None = None
    _text_line: str = ""
    _line_no: int = 0
    _col_no: int = 0

    token_map: typing.ClassVar[dict[str, Token]] = {
        "=": Token.EQL,
        "(": Token.LPAREN,
        ")": Token.RPAREN,
        "[": Token.LBRAK,
        "]": Token.RBRAK,
        "{": Token.LBRACE,
        "}": Token.RBRACE,
        "|": Token.BAR,
        ".": Token.PERIOD,
    }

    def open(self, file_name: Path) -> None:
        logger.debug(f"Opening {file_name}")
        self._file_name = file_name
        try:
            self._text = self._file_name.open("r")
        except Exception:
            print(f"[bold red]Error: Source file '{file_name}' not found[/bold red]")
            raise typer.Exit(code=1) from None
        self.get_next_char()

    def raise_error(self, msg: str) -> None:
        logger.error(msg)
        raise SyntaxError(
            msg, (self._file_name, self._line_no, self._col_no, self._text_line)
        )

    def skip_space(self) -> None:
        while self._ch.isspace():
            self.get_next_char()

    def get_next_char(self) -> None:
        while not self.eof and self._text_line == "":
            self._text_line = self._text.readline()
            self._line_no += 1
            self._col_no = 0
            if self._text_line == "":
                self.eof = True
                break
            self._text_line = self._text_line.rstrip()
        if self.eof:
            self._ch = ""
        else:
            assert self._text_line != ""
            self._ch = self._text_line[0]
            self._text_line = self._text_line[1:]
            self._col_no += 1

    def skip_comments(self):
        com_col: int = self._col_no
        com_line: int = self._line_no
        logger.debug(f"Skipping comment at line {com_line} and column {com_col}")
        self.get_next_char()
        while not self.eof:
            if self._ch == "(":
                self.get_next_char()
                if self._ch == "*":
                    self.skip_comments()
            if self._ch == "*":
                self.get_next_char()
                if self._ch == ")":
                    break
            self.get_next_char()
        if self.eof:
            self.raise_error(
                f"Unterminated comment at line {com_line} and column {com_col}"
            )
        self.get_next_char()

    def get_next_symbol(self):
        self.skip_space()

        if self._ch.isalpha():
            self.sym = Token.IDENT
            self.value = self._ch
            self.get_next_char()
            while self._ch.isalpha():
                self.value += self._ch
                self.get_next_char()

        elif self._ch == '"':
            self.sym = Token.LITERAL
            self.value = ""
            self.get_next_char()
            while not self.eof and self._ch != '"':
                self.value += self._ch
                self.get_next_char()
            if self.eof:
                self.error("Unterminated literal")
            self.get_next_char()
        elif self._ch == "":
            self.sym = Token.EOF
            self.value = ""
        elif self._ch == "(":
            self.get_next_char()
            if self._ch == "*":
                self.skip_comments()
                self.get_next_symbol()
            else:
                self.sym = Token.LPAREN
                self.value = self._ch
                return
        elif self._ch in self.token_map:
            self.sym = self.token_map[self._ch]
            self.value = self._ch
            self.get_next_char()
        else:
            self.sym = Token.OTHER
            self.value = self._ch
            self.get_next_char()
        logger.debug(f"Token: {self.sym}, Value: {self.value}")
