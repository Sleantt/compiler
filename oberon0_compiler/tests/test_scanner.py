# SPDX-FileCopyrightText: 2025 Luca Michel <luca.michel@hes-so.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

import io

from oberon0_compiler.scanner import Scanner
from oberon0_compiler.tokens import Token


def test_eof():
    src = ""
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.EOF
    assert scanner.value == "eof"
    scanner.get_next_symbol()
    assert scanner.sym == Token.EOF
    assert scanner.value == "eof"


def test_assignment():
    src = "VAR i := 0;"
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.VAR
    scanner.get_next_symbol()
    assert scanner.sym == Token.IDENT
    scanner.get_next_symbol()
    assert scanner.sym == Token.BECOMES
    scanner.get_next_symbol()
    assert scanner.sym == Token.NUMBER
    scanner.get_next_symbol()
    assert scanner.sym == Token.SEMICOLON


def test_compare_leq():
    src = "i <= 0"
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.IDENT
    assert scanner.value == "i"
    scanner.get_next_symbol()
    assert scanner.sym == Token.LEQ
    assert scanner.value == "<="
    scanner.get_next_symbol()
    assert scanner.sym == Token.NUMBER
    assert scanner.value == "0"
    scanner.get_next_symbol()
    assert scanner.sym == Token.EOF
    assert scanner.value == "eof"


def test_compare_less():
    src = "i < 1"
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.IDENT
    assert scanner.value == "i"
    scanner.get_next_symbol()
    assert scanner.sym == Token.LSS
    assert scanner.value == "<"
    scanner.get_next_symbol()
    assert scanner.sym == Token.NUMBER
    assert scanner.value == "1"


def test_alphanum_ident():
    src = "i2 >= 1"
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.IDENT
    assert scanner.value == "i2"
    scanner.get_next_symbol()
    assert scanner.sym == Token.GEQ
    assert scanner.value == ">="
    scanner.get_next_symbol()
    assert scanner.sym == Token.NUMBER
    assert scanner.value == "1"


def test_long_number():
    src = "i >= 1234"
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.IDENT
    assert scanner.value == "i"
    scanner.get_next_symbol()
    assert scanner.sym == Token.GEQ
    assert scanner.value == ">="
    scanner.get_next_symbol()
    assert scanner.sym == Token.NUMBER
    assert scanner.value == "1234"


def test_multiple_comments():
    src = "i (**)(*(*Test*)*) := 0"
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    scanner.get_next_symbol()
    assert scanner.sym == Token.IDENT
    assert scanner.value == "i"
    scanner.get_next_symbol()
    assert scanner.sym == Token.BECOMES
    assert scanner.value == ":="
    scanner.get_next_symbol()
    assert scanner.sym == Token.NUMBER
    assert scanner.value == "0"
