#lang rosette


(require rosette/lib/angelic  ; provides `choose*`
         rosette/lib/synthax  ; provides `??`
         rosette/lib/match)   ; provides `match`
; Tell Rosette we really do want to use integers.
(current-bitwidth #f)


(struct expr (identifier op digit) #:transparent)

(define (neq? a b)
  (not (eq? a b)))

(define (interpret p input)
  (let ([acceptable-consts (list 0 1 2 -1)]
        [acceptable-ops (list > < >= <= eq? neq?)]
        [ismember? (lambda (item lst) 
                       (ormap (lambda (cur) (eq? item cur))
                       lst))])
    (match p
      [(expr _ op digit) (and (ismember? digit acceptable-consts)
                              (ismember? op acceptable-ops)
                              (op input digit))])))

(define sketch
  (expr 'x [choose > < >= <= eq? neq?] [choose 0 1 2 -1]))

; command args
(define raw-args (vector->list (current-command-line-arguments)))
(define op-option (first raw-args))
(define raw-vsa (rest raw-args))
(define vsa (map (lambda (n) (string->number n)) raw-vsa))


(define identify-op
  (solve
   (begin
     (for ([i vsa])
       (cond
        [(string=? op-option "t") (assert (interpret sketch i))] ;  always true
        [else (assert (not (interpret sketch i)))]) ;  always false
       )
)))

(cond
  ([sat? identify-op] (evaluate sketch identify-op))
  (else (display "unsat")))
