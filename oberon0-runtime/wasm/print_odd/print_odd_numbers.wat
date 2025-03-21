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
  (func $odd
    ;; Allocate stack
    global.get $sp
    i32.const 8
    i32.sub
    global.set $sp

    call $open_input

    ;; Set
    global.get $sp
    i32.const 1
    i32.store

    ;; Read number
    global.get $sp
    i32.const 4
    i32.add
    call $read_int

    (block $initial
      ;; Get i
      global.get $sp
      i32.load

      ;; Get our number
      global.get $sp
      i32.const 4
      i32.add
      i32.load

      ;; Compare them and eventually break
      i32.ge_s
      br_if $initial
      (loop $my_loop
        ;; Print current i
        global.get $sp
        i32.load
        i32.const 5
        call $write_int
        call $write_ln

        ;; Get address of i to store it afterwards
        global.get $sp

        ;; Add two to $i and store the value
        global.get $sp
        i32.load
        i32.const 2
        i32.add
        i32.store

        ;; Get i
        global.get $sp
        i32.load

        ;; Get our number
        global.get $sp
        i32.const 4
        i32.add
        i32.load

        ;; Compare them and eventually break
        i32.lt_s
        br_if $my_loop
      )
    )

    ;; Restore stack
    global.get $sp
    i32.const 8
    i32.add
    global.set $sp
  )
  (export "print_odd_numbers" (func $odd))
)
