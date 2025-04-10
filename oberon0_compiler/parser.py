# SPDX-FileCopyrightText: 2025 Luca Michel <luca.michel@hes-so.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon0 Parser
"""

from loguru import logger
from pydantic import BaseModel

from oberon0_compiler.ast import (
    ArrayType,
    Assignment,
    ComplexExpression,
    ConstantDeclaration,
    Declarations,
    EmptyStatement,
    Expression,
    ExpressionFactor,
    Factor,
    FormalParameter,
    FunctionCall,
    If,
    IndexSelector,
    Module,
    Negation,
    Node,
    Number,
    ProcedureCall,
    ProcedureDeclaration,
    Repeat,
    SimpleExpression,
    SimpleFactor,
    Statement,
    StatementSequence,
    Term,
    Type,
    TypeDeclaration,
    VariableDeclaration,
    While,
)
from oberon0_compiler.scanner import Scanner
from oberon0_compiler.tokens import Token


class Parser(BaseModel):
    _relational_operators: list[Token] = [
        Token.EQL,
        Token.NEQ,
        Token.LSS,
        Token.LEQ,
        Token.GTR,
        Token.GEQ,
    ]
    scanner: Scanner
    has_error: bool = False

    def raise_error(self, msg: str) -> None:
        self.has_error = True
        self.scanner.raise_error(msg)

    def raise_expected_error(self, expected: Token) -> None:
        self.raise_error(f"Expected '{expected}' but got '{self.scanner.sym}'")

    def current_symbol(self) -> Token:
        return self.scanner.sym

    def current_value(self) -> str:
        return self.scanner.value

    def next_symbol(self) -> None:
        self.scanner.get_next_symbol()

    def expect(self, expected: Token) -> str:
        if self.current_symbol() != expected:
            self.raise_expected_error(expected)
        value: str = self.current_value()
        self.next_symbol()
        return value

    def ident(self) -> str:
        id: str = self.expect(Token.IDENT)
        logger.debug(f"Identifier with value '{id}'")
        return id

    def ident_list(self) -> list[str]:
        logger.debug("Identifier list")
        id_list: list[str] = []
        id_list.append(self.ident())
        while self.current_symbol() == Token.COMMA:
            self.next_symbol()
            id_list.append(self.ident())
        return id_list

    def actual_parameters(self) -> list[Expression]:
        logger.debug("Function parameters")
        exprs: list[Expression] = []
        self.expect(Token.LPAREN)
        # The expression will always begin with either a + or - (SimpleExpression)
        # or an ident (term -> factor -> ident)
        if self.current_symbol() in [
            Token.PLUS,
            Token.MINUS,
            Token.IDENT,
            Token.NUMBER,
            Token.LPAREN,
            Token.NOT,
        ]:
            exprs.append(self.expression())
            while self.current_symbol() == Token.COMMA:
                self.next_symbol()
                exprs.append(self.expression())

        self.expect(Token.RPAREN)
        return exprs

    def selector(self) -> list[IndexSelector]:
        logger.debug("Selector")
        select: list[IndexSelector] = []
        while self.current_symbol() == Token.LBRACK:
            self.expect(Token.LBRACK)
            select.append(IndexSelector(expression=self.expression()))
            self.expect(Token.RBRACK)
        return select

    def ident_factor(self) -> Factor:
        logger.debug("Identifier factor")
        id = self.ident()
        if self.current_symbol() == Token.LPAREN:
            # Function call
            params: list[Expression] = self.actual_parameters()
            return FunctionCall(ident=id, params=params)
        else:
            # Selector or simple ident
            return SimpleFactor(ident=id, selector=self.selector())

    def factor(self) -> Factor:
        logger.debug("Factor")
        if self.current_symbol() == Token.IDENT:
            # Ident
            return self.ident_factor()
        elif self.current_symbol() == Token.NUMBER:
            # Number
            return Number(value=int(self.expect(Token.NUMBER)))
        elif self.current_symbol() == Token.LPAREN:
            # Expression
            self.expect(Token.LPAREN)
            expr = self.expression()
            self.expect(Token.RPAREN)
            return ExpressionFactor(expression=expr)
        elif self.current_symbol() == Token.NOT:
            # Negation
            self.next_symbol()
            return Negation(factor=self.factor())

        self.raise_error(
            f"Invalid factor, expected either '{Token.IDENT}',\
            '{Token.NUMBER}', '{Token.LPAREN}' or '{Token.NOT}'"
        )

    def term(self) -> Term:
        logger.debug("Term")
        fact = self.factor()
        mulop_factors: list[tuple[str, Factor]] = []
        while self.current_symbol() in [Token.TIMES, Token.DIV, Token.MOD, Token.AND]:
            operator: str = self.current_value()
            self.next_symbol()
            mulop_factors.append((operator, self.factor()))
        return Term(factor=fact, mulop_factors=mulop_factors)

    def simple_expression(self) -> SimpleExpression:
        logger.debug("Simple expression")
        sign: str | None = None
        if self.current_symbol() in [Token.PLUS, Token.MINUS]:
            sign = self.current_value()
        t: Term = self.term()
        addop_terms: list[tuple[str, Term]] = []
        while self.current_symbol() in [Token.PLUS, Token.MINUS, Token.OR]:
            operator = self.current_value()
            self.next_symbol()
            addop_terms.append((operator, self.term()))
        return SimpleExpression(sign=sign, term=t, addop_terms=addop_terms)

    def expression(self) -> Expression:
        logger.debug("Expression")
        simple_expr: SimpleExpression = self.simple_expression()
        if self.current_symbol() in self._relational_operators:
            operator = self.current_value()
            self.next_symbol()
            second_expression = self.simple_expression()
            return ComplexExpression(
                simple_expression=simple_expr,
                relation=(operator, second_expression),
            )
        return simple_expr

    def type(self) -> Type:
        if self.current_symbol() == Token.IDENT:
            logger.debug("Simple type")
            id = self.ident()
            return Type(ident=id)
        logger.debug("Array type")
        self.expect(Token.ARRAY)
        expr: Expression = self.expression()
        self.expect(Token.OF)
        t: Type = self.type()
        logger.debug(expr.__str__())
        return ArrayType(ident="", size=expr, type=t)

    def repeat_statement(self) -> Repeat:
        logger.debug("Repeat")
        self.expect(Token.REPEAT)
        stat_seq: StatementSequence = self.statement_sequence()
        self.expect(Token.UNTIL)
        expr: Expression = self.expression()
        return Repeat(body=stat_seq, condition=expr)

    def if_statement(self) -> If:
        logger.debug("If")
        self.expect(Token.IF)
        expr = self.expression()
        self.expect(Token.THEN)
        stat_seq = self.statement_sequence()
        elsif: list[tuple[Expression, StatementSequence]] = []
        else_: StatementSequence = None
        while self.current_symbol() == Token.ELSIF:
            self.expect(Token.ELSIF)
            elsif_expr = self.expression()
            self.expect(Token.THEN)
            elsif_stat_seq = self.statement_sequence()
            elsif.append(
                tuple[Expression, StatementSequence](elsif_expr, elsif_stat_seq)
            )
        if self.current_symbol() == Token.ELSE:
            self.expect(Token.ELSE)
            else_ = self.statement_sequence()
        self.expect(Token.END)
        return If(
            condition=expr,
            then=stat_seq,
            elsif=elsif,
            else_=else_,
        )

    def while_statement(self) -> While:
        logger.debug("While")
        self.expect(Token.WHILE)
        expr = self.expression()
        self.expect(Token.DO)
        stat_seq = self.statement_sequence()
        self.expect(Token.END)
        return While(
            condition=expr,
            body=stat_seq,
        )

    def statement(self) -> Statement:  # noqa: PLR0911
        logger.debug("Statement")
        if self.current_symbol() == Token.IDENT:
            logger.debug("Assignement or procedure call")
            # Assignement or Procedure call
            id = self.ident()
            select = self.selector()
            if self.current_symbol() == Token.BECOMES:
                self.next_symbol()
                # Assignement
                return Assignment(
                    ident=id, selector=select, expression=self.expression()
                )

            # Procedure call
            if self.current_symbol() == Token.LPAREN:
                # With parameters
                return ProcedureCall(
                    ident=id, selector=select, params=self.actual_parameters()
                )
            return ProcedureCall(ident=id, selector=select, params=[])
        elif self.current_symbol() == Token.WHILE:
            return self.while_statement()
        elif self.current_symbol() == Token.IF:
            return self.if_statement()
        elif self.current_symbol() == Token.REPEAT:
            return self.repeat_statement()
        return EmptyStatement()

    def statement_sequence(self) -> StatementSequence:
        logger.debug("Statement sequence")
        stat_seq: list[Statement] = []
        stat_seq.append(self.statement())
        while self.current_symbol() == Token.SEMICOLON:
            self.next_symbol()
            stat_seq.append(self.statement())
        return StatementSequence(statements=stat_seq)

    def formal_parameter(self) -> FormalParameter:
        logger.debug("Formal parameter")
        by_ref: bool = False
        if self.current_symbol() == Token.VAR:
            self.next_symbol()
            by_ref = True
        id_list: list[str] = self.ident_list()
        self.expect(Token.COLON)
        t = self.type()
        return FormalParameter(by_ref=by_ref, ident_list=id_list, type=t)

    def formal_parameters(self) -> list[FormalParameter]:
        logger.debug("Formal parameters")
        fp: list[FormalParameter] = []
        self.expect(Token.LPAREN)

        if self.current_symbol() in [Token.VAR, Token.IDENT]:
            fp.append(self.formal_parameter())
            while self.current_symbol() == Token.SEMICOLON:
                self.next_symbol()
                fp.append(self.formal_parameter())
        self.expect(Token.RPAREN)
        return fp

    def const_declarations(self) -> list[ConstantDeclaration]:
        logger.debug("Constant declarations")
        const_decl: list[ConstantDeclaration] = []
        if self.current_symbol() == Token.CONST:
            self.next_symbol()
            if self.current_symbol() == Token.IDENT:
                id: str = self.ident()
                while True:
                    self.expect(Token.EQL)
                    expr: Expression = self.expression()
                    self.expect(Token.SEMICOLON)
                    const_decl.append(
                        ConstantDeclaration(
                            ident=id,
                            expression=expr,
                        )
                    )
                    if self.current_symbol() != Token.IDENT:
                        break
                    id = self.ident()
        return const_decl

    def type_declarations(self) -> list[TypeDeclaration]:
        logger.debug("Type declarations")
        type_decl: list[TypeDeclaration] = []

        if self.current_symbol() == Token.TYPE:
            self.next_symbol()
            if self.current_symbol() == Token.IDENT:
                id: str = self.ident()
                while True:
                    self.expect(Token.EQL)
                    t: Type = self.type()
                    self.expect(Token.SEMICOLON)
                    type_decl.append(TypeDeclaration(ident=id, type=t))
                    if self.current_symbol() != Token.IDENT:
                        break
                    id = self.ident()

        return type_decl

    def variable_declarations(self) -> list[VariableDeclaration]:
        logger.debug("Variables declarations")
        var_decl: list[VariableDeclaration] = []

        if self.current_symbol() == Token.VAR:
            self.next_symbol()
            if self.current_symbol() == Token.IDENT:
                id_list: list[str] = self.ident_list()
                while True:
                    self.expect(Token.COLON)
                    t: Type = self.type()
                    self.expect(Token.SEMICOLON)
                    var_decl.append(VariableDeclaration(ident_list=id_list, type=t))
                    if self.current_symbol() != Token.IDENT:
                        break
                    id_list: list[str] = self.ident_list()
        logger.debug("End of variables declarations")
        return var_decl

    def procedure_declarations(self) -> list[ProcedureDeclaration]:
        logger.debug("Procedures declarations")
        procedure_decl: list[ProcedureDeclaration] = []

        while self.current_symbol() == Token.PROCEDURE:
            self.next_symbol()
            # Heading
            id: str = self.ident()
            exported: bool = False
            if self.current_symbol() == Token.TIMES:
                exported = True
                self.next_symbol()
            formal_params: list[FormalParameter] = []
            if self.current_symbol() == Token.LPAREN:
                formal_params = self.formal_parameters()

            self.expect(Token.SEMICOLON)

            # Body
            decl: Declarations = self.declarations()
            body = None
            if self.current_symbol() == Token.BEGIN:
                # Has a statement sequence
                self.next_symbol()
                body = self.statement_sequence()
            self.expect(Token.END)
            closing_id = self.ident()
            if id != closing_id:
                # Unterminated procedure
                self.raise_error(
                    f"Unexpected identifier when closing a procedure.\
                        Expected '{id}' but got '{closing_id}'"
                )
            procedure_decl.append(
                ProcedureDeclaration(
                    ident=id,
                    exported=exported,
                    params=formal_params,
                    declarations=decl,
                    body=body,
                )
            )
            self.expect(Token.SEMICOLON)
        # End of the procedure declaration

        return procedure_decl

    def declarations(self) -> Declarations:
        logger.debug("Declarations")
        const_decl: list[ConstantDeclaration] = self.const_declarations()
        type_decl: list[TypeDeclaration] = self.type_declarations()
        var_decl: list[VariableDeclaration] = self.variable_declarations()
        procedure_decl: list[ProcedureDeclaration] = self.procedure_declarations()

        return Declarations(
            const_declarations=const_decl,
            type_declarations=type_decl,
            var_declarations=var_decl,
            procedure_declarations=procedure_decl,
        )

    def module(self) -> Module:
        logger.debug("Module")
        self.expect(Token.MODULE)
        id: str = self.ident()
        self.expect(Token.SEMICOLON)
        decl: Declarations = self.declarations()
        stat_seq: StatementSequence = StatementSequence(statements=[])
        if self.current_symbol() == Token.BEGIN:
            self.next_symbol()
            stat_seq = self.statement_sequence()
        self.expect(Token.END)
        closing_id: str = self.ident()

        if id != closing_id:
            # Unterminated module
            self.raise_error(
                f"Unexpected identifier when closing a module.\
                    Expected '{id}' but got '{closing_id}'"
            )
        self.expect(Token.PERIOD)
        module: Module = Module(ident=id, declarations=decl, body=stat_seq)
        return module

    def parse(self) -> Node:
        self.scanner.get_next_symbol()
        tree = self.module()
        print(tree)
        return tree
