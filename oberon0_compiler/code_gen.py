# SPDX-FileCopyrightText: 2025 Luca Michel <luca.michel@hes-so.ch>
#
# SPDX-License-Identifier: Apache-2.0 OR MIT

"""
Oberon-2 WASM Code Generator
"""

from typing import ClassVar

import wasm_gen as W  # noqa
from loguru import logger
from pydantic import BaseModel
from wasm_gen import Function
from wasm_gen import instructions as I  # noqa
from wasm_gen.type import i32_t

from oberon0_compiler import ast, sym_table
from oberon0_compiler.ast import (
    Assignment,
    ComplexExpression,
    EmptyStatement,
    Expression,
    Factor,
    FunctionCall,
    If,
    Number,
    ProcedureCall,
    Repeat,
    SimpleExpression,
    SimpleFactor,
    Statement,
    Term,
    While,
)
from oberon0_compiler.sym_table import (
    Symbol,
    SymbolTable,
    SystemCall,
)


class CodeGenError(Exception):
    def __init__(self, message, file_name, line_no, col_no):
        super().__init__(message)
        self.file_name = file_name
        self.line_no = line_no
        self.col_no = col_no


class CodeGenerator(BaseModel):
    ast_: ast.Node  # not named "ast" to avoid confusion with the module
    code: W.Module = None

    _sp: W.Global = None
    _current_function: list[W.Function] = []
    _symbol_table: ClassVar[SymbolTable] = SymbolTable()

    def check(self, condition, message):
        if not condition:
            logger.error(self._symbol_table)
            raise CodeGenError(
                message,
                self.ast_.file_name,
                self.ast_.line_no,
                self.ast_.col_no,
            )

    def symbol_from_ident(self, ident: str, class_=None) -> Symbol:
        sym = self._symbol_table.find(ident, class_=class_)
        self.check(sym is not None, f"Unknown symbol: {ident}")
        return sym

    def current_function(self) -> Function:
        assert len(self._current_function) > 0
        return self._current_function[-1]

    def add_syscalls(self):
        logger.debug("Adding system calls")

        integer: sym_table.Type = self._symbol_table.find(
            "INTEGER", class_=sym_table.Type, max_level=1
        )

        assert integer is not None
        logger.debug(f"INTEGER: {integer}")

        syscalls = [
            (
                "OpenInput",
                W.BaseFunction(type=W.FunctionType(params=[], results=[])),
                [],
                None,
            ),
            (
                "ReadInt",
                W.BaseFunction(type=W.FunctionType(params=[i32_t], results=[])),
                [sym_table.Argument(index=0, type=integer, by_ref=True)],
                None,
            ),
            (
                "eot",
                W.BaseFunction(type=W.FunctionType(params=[], results=[i32_t])),
                [],
                integer,
            ),
            (
                "WriteChar",
                W.BaseFunction(type=W.FunctionType(params=[i32_t], results=[])),
                [sym_table.Argument(index=0, type=integer, by_ref=False)],
                None,
            ),
            (
                "WriteInt",
                W.BaseFunction(type=W.FunctionType(params=[i32_t, i32_t], results=[])),
                [
                    sym_table.Argument(index=0, type=integer, by_ref=False),
                    sym_table.Argument(index=1, type=integer, by_ref=False),
                ],
                None,
            ),
            (
                "WriteLn",
                W.BaseFunction(type=W.FunctionType(params=[], results=[])),
                [],
                None,
            ),
        ]

        for name, f, args, ret in syscalls:
            self.code.imports.append(W.Import(node=f, module="sys", name=name))
            self._symbol_table.add(
                sym_table.SystemCall(
                    name=name, arguments=args, return_type=ret, syscall=f
                ),
            )

    def add_memory(self):
        m1 = W.BaseMemory(type=W.MemoryType(min_pages=1))
        self.code.imports.append(W.Import(node=m1, module="env", name="memory"))

    def add_stack_pointer(self):
        self._sp = W.BaseGlobal(type=W.GlobalType(type=i32_t, mutable=True))
        self.code.imports.append(
            W.Import(node=self._sp, module="env", name="__stack_pointer")
        )

    def type_of(self, type: ast.Type) -> sym_table.Type:
        integer = self._symbol_table.find("INTEGER", class_=sym_table.Type, max_level=1)
        boolean = self._symbol_table.find("BOOLEAN", class_=sym_table.Type, max_level=1)
        if isinstance(type, ast.NamedType) and type.ident == "INTEGER":
            return integer
        elif isinstance(type, ast.NamedType) and type.ident == "BOOLEAN":
            return boolean
        elif isinstance(type, ast.NamedType):
            raise Exception(f"Unknown type: {type.ident} (Not yet implemented)")
        else:
            raise Exception(f"Unknown type: {type} (Not yet implemented)")

    def addr_of_expr(self, expr):
        self.check(isinstance(expr, ast.SimpleExpression), "Expression expected")
        self.check(expr.sign is None, "Sign not allowed")
        self.check(
            isinstance(expr.term.factor, ast.SimpleFactor), "Simple factor expected"
        )
        self.check(len(expr.term.mulop_factors) == 0, "No mulop factors allowed")
        self.check(len(expr.addop_terms) == 0, "No addop terms allowed")

        sym = self.symbol_from_ident(expr.term.factor.ident)
        self.addr_of_sym(sym)

    def addr_of_sym(self, sym):
        if isinstance(sym, sym_table.LocalVariable):
            self.current_function().body.extend(
                [
                    I.GlobalGet(global_=self._sp),
                    I.I32Const(value=sym.offset),
                    I.I32Add(),
                ]
            )
        elif isinstance(sym, sym_table.GlobalVariable):
            self.current_function().body.extend(
                [
                    I.I32Const(value=sym.offset),
                ]
            )
        else:
            raise Exception(f"Unknown symbol: {sym} (NOT YET IMPLEMENTED)")

    def function_call(self, f):
        s = self._symbol_table.find(f.ident)
        integer = self._symbol_table.find("INTEGER", class_=sym_table.Type, max_level=1)
        self.check(s is not None, f"Unknown function: {f.ident}")
        self.check(isinstance(s, sym_table.SystemCall), "Only system calls allowed")
        self.check(s.return_type == integer, "Return type must be INTEGER")
        self.system_call(f, s)

    def factor(self, f: Factor) -> sym_table.Type:
        self.check(not isinstance(f, FunctionCall), "Function calls not supported")
        if isinstance(f, Number):
            self.current_function().body.append(I.I32Const(value=f.value))

    def term(self, t: Term) -> sym_table.Type:
        self.check(len(t.mulop_factors) == 0, "Signs not supported")
        return self.factor(t.factor)

    def simple_expression(self, expr: SimpleExpression) -> sym_table.Type:
        self.check(expr.sign is None, "Signs not supported")
        self.check(len(expr.addop_terms) == 0, "Signs not supported")
        return self.term(expr.term)

    def complex_expression(self, expr: ComplexExpression) -> sym_table.Type:
        # TODO
        pass

    def expression(self, expr: Expression) -> sym_table.Type:
        if isinstance(expr, SimpleExpression):
            return self.simple_expression(expr)
        if isinstance(expr, ComplexExpression):
            return self.complex_expression(expr)
        self.check(False, "Unsupported expression type")

    def assignment(self, a: Assignment):
        sym = self.symbol_from_ident(
            ident=a.ident,
            class_=sym_table.Variable,
        )

        if isinstance(sym, sym_table.Constant):
            self.check(False, "Cannot assign a value to a constant")

        # Get address of variable
        self.addr_of_sym(sym)

        # Evaluate expression and get its type
        _ = self.expression(a.expression)

        self.current_function().body.append(I.I32Store())

    def system_call(self, p, s: SystemCall):
        # TODO
        pass

    def while_loop(self, w: While):
        # TODO
        pass

    def repeat_loop(self, w: Repeat):
        # TODO
        pass

    def if_statement(self, i: If):
        # TODO
        pass

    def statement_sequence(self, statements: list[Statement]):
        for s in statements:
            if isinstance(s, EmptyStatement):
                pass
            elif isinstance(s, Assignment):
                self.assignment(s)
            else:
                self.check(False, "Unsupported statement")

    def procedure_call(self, p: ProcedureCall):
        # TODO
        pass

    def procedure(self, p):
        if p.exported:
            self.check(
                len(p.params) == 0,
                "Exported procedures cannot have parameters",
            )

        f = W.Function(type=W.FunctionType(params=[], results=[]))
        self._current_function.append(f)

        index = 0
        for par in p.params:
            t = self.type_of(par.type)
            for _ in par.ident_list:
                self._symbol_table.add(
                    sym_table.Argument(
                        index=index,
                        type=t,
                        by_ref=par.by_ref,
                    )
                )
                index += 1

        ptr = 0
        for vl in p.declarations.var_declarations:
            type = self._symbol_table.find(vl.type.ident, class_=sym_table.Type)
            self.check(type is not None, f"Unknown type: {vl.type.ident}")
            for v in vl.ident_list:
                self._symbol_table.add(
                    sym_table.LocalVariable(
                        name=v,
                        type=type,
                        offset=ptr,
                    )
                )
                ptr += type.size

        # Procedure preamble (make room for local variables)
        if ptr > 0:
            f.body.extend(
                [
                    I.GlobalGet(global_=self._sp),
                    I.I32Const(value=ptr),
                    I.I32Sub(),
                    I.GlobalSet(global_=self._sp),
                ]
            )

        self.statement_sequence(p.body.statements)

        # Procedure postamble (reclaim memory for local variables)
        if ptr > 0:
            f.body.extend(
                [
                    I.GlobalGet(global_=self._sp),
                    I.I32Const(value=ptr),
                    I.I32Add(),
                    I.GlobalSet(global_=self._sp),
                ]
            )

        f.body.append(I.End())
        self.code.funcs.append(f)
        if p.exported:
            self.code.exports.append(W.Export(node=f, name=p.ident))

        self._current_function.pop()

    def global_variable(self, variables):
        addr = 0
        integer = self._symbol_table.find("INTEGER", class_=sym_table.Type, max_level=1)
        boolean = self._symbol_table.find("BOOLEAN", class_=sym_table.Type, max_level=1)

        for v in variables:
            if v.type.ident == "INTEGER":
                type = integer
            elif v.type.ident == "BOOLEAN":
                type = boolean
            else:
                raise Exception(f"Type {v.type.ident} not yet supported")

            for i in v.ident_list:
                self._symbol_table.add(
                    sym_table.GlobalVariable(
                        name=i,
                        type=type,
                        offset=addr,
                    )
                )
                addr += type.size

    def generate(self, io):
        # Start with an empty symbol table
        CodeGenerator._symbol_table = SymbolTable()

        self.check(isinstance(self.ast_, ast.Module), "Module expected")
        self._symbol_table.new_scope()
        self.code = W.Module()

        self._symbol_table.add(
            sym_table.Type(name="INTEGER", type=ast.Type(ident="INTEGER"), size=4)
        )
        self._symbol_table.add(
            sym_table.Type(name="BOOLEAN", type=ast.Type(ident="BOOLEAN"), size=4)
        )

        self.add_syscalls()
        self.add_memory()
        self.add_stack_pointer()

        d = self.ast_.declarations
        for _ in d.type_declarations:
            raise Exception("Types not yet implemented")
        for _ in d.const_declarations:
            raise Exception("Constants not yet implemented")
        self.global_variable(d.var_declarations)
        for p in d.procedure_declarations:
            self.procedure(p)

        io.write(bytes(self.code))
