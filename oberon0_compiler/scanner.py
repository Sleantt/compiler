# SPDX-FileCopyrightText: 2025 Luca Michel <luca.michel@hes-so.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-0 scanner
"""

import io
import typing
from enum import Enum
from pathlib import Path

from loguru import logger
from pydantic import BaseModel

from oberon0_compiler.tokens import Token, token_str


class Scanner(BaseModel):
    eof: bool = False
    sym: Enum | None = None  # Next Symbol
    value: str = ""

    _ch: str = ""
    _file_name: Path | None = None
    _text: typing.TextIO | None = None
    _text_line: str = ""
    _line_no: int = 0
    _col_no: int = 0

    _keyword = {str(i): i for i in Token if str(i).isupper()}
    _symbol = {
        str(i): i for i in Token if not str(i).isupper() and not str(i).islower()
    }

    def open(self, text: io.TextIOBase) -> None:
        self._text = text
        if hasattr(text, "name"):
            self._file_name = Path(text.name)
        else:
            self._file_name = None

        self.get_next_char()

    def raise_error(self, msg: str) -> None:
        logger.error(msg)
        raise SyntaxError(
            msg, (self._file_name, self._line_no, self._col_no, self._text_line)
        )

    def skip_space(self):
        while self._ch.isspace():
            self.get_next_char()

    def skip_comment(self):
        while True:
            self.get_next_char()
            if self.eof:
                self.error("Unterminated comment")
                return
            if self._ch == "(":
                self.get_next_char()
                if self._ch == "*":
                    self.get_next_char()
                    self.skip_comment()
            if self._ch == "*":
                self.get_next_char()
                if self._ch == ")":
                    self.get_next_char()
                    return

    def get_next_char(self):
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

    def token(self) -> tuple[Token, str]:
        current: str = self._ch
        self.get_next_char()
        while current + self._ch in self._symbol:
            if self._ch == "":
                break
            current += self._ch
            self.get_next_char()
        return (self._symbol[current], current)

    def get_next_symbol(self):  # noqa: C901
        self.sym = None

        while True:
            self.skip_space()

            if self._ch.isalpha():
                # Identifier
                self.sym = Token.IDENT
                self.value = self._ch
                self.get_next_char()
                while self._ch.isalnum():
                    self.value += self._ch
                    self.get_next_char()
                if (kw := self.value) in self._keyword:
                    # Identifier is a keyword
                    self.sym = self._keyword[kw]
            elif self._ch.isdigit():
                # Number
                self.sym = Token.NUMBER
                self.value = self._ch
                self.get_next_char()
                while self._ch.isdigit():
                    self.value += self._ch
                    self.get_next_char()
            elif self._ch in self._symbol:
                # Symbol
                self.sym, self.value = self.token()
                if self.sym == Token.LPAREN:
                    if self._ch == "*":
                        # Symbol is a comment start
                        self.sym = None
                        self.get_next_char()
                        self.skip_comment()
            elif self._ch == "":
                # End of file
                self.sym = Token.EOF
                self.value = token_str["EOF"]

            if self.sym is not None:
                # Skipped comment, redo
                logger.debug(f"Symbol '{self.sym}' with value '{self.value}'")
                break
