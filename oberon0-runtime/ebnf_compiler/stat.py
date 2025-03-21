# SPDX-FileCopyrightText: 2025 Jacques Supcik <jacques.supcik@hefr.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
AST Statistics
"""

import ebnf_compiler.ast0 as ast


def symbols(root: ast.Syntax) -> tuple[set[str], set[str]]:  # noqa: C901
    non_terminals: set[str] = set()
    terminals: set[str] = set()

    def term(node: ast.Term):
        for f in node.factors:
            if isinstance(f, ast.Identifier):
                if f.value not in root.symbols:
                    terminals.add(f.value)
            elif isinstance(f, ast.Literal):
                terminals.add(f.value)
            elif isinstance(f, ast.Expression):
                expression(f)
            elif isinstance(f, ast.Option):
                expression(f.expr)
            elif isinstance(f, ast.Repetition):
                expression(f.expr)

    def expression(node: ast.Expression):
        for t in node.terms:
            term(t)

    for p in root.production:
        expression(p.expression)
        non_terminals.add(p.identifier.value)

    return non_terminals, terminals
