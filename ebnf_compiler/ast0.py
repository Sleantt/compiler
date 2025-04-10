# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
EBNF Abstract Syntax Tree
"""

from typing import ClassVar

from pydantic import BaseModel


class Node(BaseModel):
    symbols: ClassVar[dict[str, "Expression"]] = {}


class Factor(Node):
    pass


class Term(Node):
    factors: list[Factor]

    def __str__(self) -> str:
        return " ".join(f"{f}" for f in self.factors)


class Identifier(Factor):
    value: str

    def __str__(self) -> str:
        return self.value


class Literal(Factor):
    value: str

    def __str__(self) -> str:
        return f'"{self.value}"'


class Expression(Factor):
    terms: list[Term]
    paren: bool = False

    def __str__(self) -> str:
        body = " | ".join(f"{t}" for t in self.terms)
        if self.paren:
            return f"( {body} )"
        return body


class Option(Factor):
    expr: Expression

    def __str__(self) -> str:
        return f"[ {self.expr} ]"


class Repetition(Factor):
    expr: Expression

    def __str__(self) -> str:
        return f"{{ {self.expr} }}"


class Production(Node):
    identifier: Identifier
    expression: Expression

    def model_post_init(self, context):
        if self.identifier.value in self.symbols:
            raise ValueError(f"Symbol {self.identifier.value} already defined")
        Node.symbols[self.identifier.value] = self.expression

    def __str__(self) -> str:
        return f"{self.identifier} = {self.expression}."


class Syntax(Node):
    production: list[Production]

    def __str__(self) -> str:
        return "\n".join(f"{p}" for p in self.production)
