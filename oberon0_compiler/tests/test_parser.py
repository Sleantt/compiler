import io

from oberon0_compiler.ast import EmptyStatement, Module
from oberon0_compiler.parser import Parser
from oberon0_compiler.scanner import Scanner


def test_simple_program():
    src = "MODULE Test;\
        PROCEDURE Say42*;\
            VAR x: INTEGER;\
        BEGIN\
            x := 42;\
        END Say42;\
        END Test."
    scanner = Scanner()
    scanner.open(io.StringIO(src))
    parser = Parser(scanner=scanner)
    ast = parser.parse()

    assert isinstance(ast, Module)

    module: Module = ast
    assert module.ident == "Test"

    declarations = module.declarations
    print(module.body)

    empty_statements_only(declarations.const_declarations)
    empty_statements_only(declarations.type_declarations)
    empty_statements_only(declarations.var_declarations)

    procedure_declarations = declarations.procedure_declarations

    assert len(procedure_declarations) == 1

    say42 = procedure_declarations[0]

    assert say42.ident == "Say42"
    assert say42.exported
    empty_statements_only(say42.params)

    declarations = say42.declarations

    empty_statements_only(declarations.const_declarations)
    empty_statements_only(declarations.type_declarations)
    empty_statements_only(declarations.procedure_declarations)

    var_decl = declarations.var_declarations

    assert len(var_decl) == 1


def empty_statements_only(elts: list):
    assert all(isinstance(x, EmptyStatement) for x in elts), (
        f"Expected only empty statements in {elts}"
    )
