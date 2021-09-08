## Examples Showing Why One-Line If, While, or For-Loop Statement is Problematic

Take the following one-line if statement for example:

```C
if(isTrue(x)) y = 0;
```

To simplify the example, assumed that the tool infers that variable `y` has a value of `{0}` and insert opaque predicate after the instruction like such: `y=0;if x!=0 {[obfuscation]}`.

However, the inserted opaque predicate is only correct if `if x!=0 {[obfuscation]}` is in the same scope as `y=0;`, which is not true in the case of this one-line if statement.

Same can be said for the following one-line while and for-loop:

```C
while(isTrue(x)) y = 0;
```
```C
for(int x=0; x<10; x++) y = 0;
```
