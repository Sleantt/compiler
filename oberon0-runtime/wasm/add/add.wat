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
  (func $add
    ;; Free stack
    global.get $sp
    i32.const 12
    i32.sub
    global.set $sp

    call $open_input

    ;; Read x
    global.get $sp
    call $read_int

    ;;  Read y
    global.get $sp
    i32.const 4
    i32.add
    call $read_int

    ;; Put address of z on the stack
    global.get $sp
    i32.const 8
    i32.add

    ;; Load x
    global.get $sp
    i32.load

    ;; Load y
    global.get $sp
    i32.const 4
    i32.add
    i32.load

    ;; Add x and y
    i32.add

    ;; Save at z address
    i32.store

    ;; Load z
    global.get $sp
    i32.const 8
    i32.add
    i32.load
    i32.const 1
    call $write_int

    call $write_ln

    ;; Restore stack
    global.get $sp
    i32.const 12
    i32.add
    global.set $sp

  )
  (export "add" (func $add))
)
