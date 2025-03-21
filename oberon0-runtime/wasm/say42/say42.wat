;; SPDX-FileCopyrightText: 2025 Luca Michel <luca.michel@hes-so.ch>
;;
;; SPDX-License-Identifier: Apache-2.0 OR MIT
(module
    (import "sys" "OpenInput" (func $open_input))
    (import "sys" "ReadInt" (func $read_int (param i32)))
    (import "sys" "eot" (func $eot (result i32)))
    (import "sys" "WriteChar" (func $write_char (param i32)))
    (import "sys" "WriteInt" (func $write_int (param i32 i32)))
    (import "sys" "WriteLn" (func $write_ln))
    (import "env" "memory" (memory 1))
    (import "env" "__stack_pointer" (global $sp (mut i32)))
  (func $say42
    i32.const 42
    i32.const 2
    call $write_int
    call $write_ln
  )
  (export "say42" (func $say42))
)
