# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
EBNF Parser
"""

from loguru import logger
from pydantic import BaseModel

from ebnf_compiler.ast0 import (
    Expression,
    Factor,
    Identifier,
    Literal,
    Production,
    Syntax,
    Term,
)
from ebnf_compiler.scanner import Scanner
from ebnf_compiler.tokens import Token


class Parser(BaseModel):
    scanner: Scanner
    has_error: bool = False

    def raise_error(self, msg: str) -> None:
        self.has_error = True
        self.scanner.raise_error(msg)

    def raise_expected_error(self, expected: Token):
        self.raise_error(f"Expected '{expected}', but got '{self.scanner.sym}'")

    def factor(self) -> Factor:
        logger.debug("Factor")
        sym = self.scanner.sym
        ident = self.scanner.value
        if sym == Token.IDENT:
            self.scanner.get_next_symbol()
            return Identifier(value=ident)
        elif sym == Token.LITERAL:
            self.scanner.get_next_symbol()
            return Literal(value=ident)
        elif sym == Token.LPAREN:
            self.scanner.get_next_symbol()
            expr: Expression = self.expression()
            expr.paren = True
            if self.scanner.sym != Token.RPAREN:
                self.raise_expected_error(Token.RPAREN)
            self.scanner.get_next_symbol()
            return expr
        elif sym == Token.LBRAK:
            self.scanner.get_next_symbol()
            expr = self.expression()
            if self.scanner.sym != Token.RBRAK:
                self.raise_expected_error(Token.RBRAK)
            self.scanner.get_next_symbol()
            return expr
        elif sym == Token.LBRACE:
            self.scanner.get_next_symbol()
            expr = self.expression()
            if self.scanner.sym != Token.RBRACE:
                self.raise_expected_error(Token.RBRACE)
            self.scanner.get_next_symbol()
            return expr
        else:
            self.raise_error(
                f"Expected identifier, literal, (', '['. or '{{' got {sym}"
            )

    def term(self) -> Term:
        logger.debug("Term")

        ter: Term = Term(factors=[])
        ter.factors.append(self.factor())
        while self.scanner.sym in (
            Token.IDENT,
            Token.LITERAL,
            Token.LPAREN,
            Token.LBRAK,
            Token.LBRACE,
        ):
            ter.factors.append(self.factor())
        return ter

    def expression(self) -> Expression:
        logger.debug("Expression")

        expr: Expression = Expression(terms=[])
        expr.terms.append(self.term())

        while self.scanner.sym == Token.BAR:
            self.scanner.get_next_symbol()
            expr.terms.append(self.term())
        return expr

    def production(self) -> Production:
        logger.debug("Production")

        ident = self.scanner.value

        self.scanner.get_next_symbol()
        if self.scanner.sym != Token.EQL:
            self.raise_expected_error(Token.EQL)

        self.scanner.get_next_symbol()
        expr = self.expression()

        if self.scanner.sym != Token.PERIOD:
            self.raise_expected_error(Token.PERIOD)
        self.scanner.get_next_symbol()

        return Production(identifier=Identifier(value=ident), expression=expr)

    def syntax(self) -> Syntax:
        logger.debug("Syntax")
        syn: Syntax = Syntax(production=[])
        while self.scanner.sym != Token.EOF:
            if self.scanner.sym != Token.IDENT:
                self.raise_expected_error(Token.IDENT)
            syn.production.append(self.production())
        return syn

    def parse(self) -> Syntax:
        logger.debug("Parsing")
        self.scanner.get_next_symbol()
        syn = self.syntax()
        print(syn)
        return syn
