## Examples Showing Why One-Line If, While, or For-Loop Statement is Problematic

Take the following one-line if statement for example:

```C
if(isTrue(x)) y = 0;
```

To simplify the example, assumed a simple value set where the tool infers that variable `y` has a value set of `{0}` and insert an opaque predicate after the instruction like such: `y=0;if y!=0 {[obfuscation]}`.

However, the inserted opaque predicate is only correct if `if y!=0 {[obfuscation]}` is in the same scope as `y=0;`, which is not true in the case of this one-line if statement.

Same can be said for the following one-line while and for-loop:

```C
while(isTrue(x)) y = 0;
```
```C
for(int x=0; x<10; x++) y = 0;
```

Note that this type of one-liner will not be problematic though: 
```C
isTrue(x) ? y=0 : y=1;
```

This is because Frama-C will internally represent that line of code as `tmp_*=0` and `tmp_*=1` and our tool will ignore value sets whose corresponding variable's name starts with `tmp_` since that is the naming convention Frama-C uses to represent intermediate variables.
