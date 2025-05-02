import io
from pathlib import Path

from wasm_gen import Module

from oberon0_compiler.code_gen import CodeGenerator
from oberon0_compiler.parser import Parser
from oberon0_compiler.scanner import Scanner


def test_say42():
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
    code_generator = CodeGenerator(ast_=ast, code=Module())
    dest = io.BytesIO()
    code_generator.generate(dest)
    with open(Path(__file__).parent / "codegen/say42.wasm", "rb") as target:
        assert target.read() == dest.getvalue()
