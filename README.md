# PyAIG: A simpe Python AIG and Truth Table package

## AIG

And-Inverter Graph ([AIG](https://en.wikipedia.org/wiki/And-inverter_graph)) is a data structure for logic synthesis and verification. The code follows the [AIGER](http://fmv.jku.at/aiger/) conventions.

## Installation

## Truth Tables example

### Import the package

```python
from pyaig import *
```

### Create the truth table manger - the max number of variables is required

``` pyhton
m = truth_tables(6, "ABCDEF")
```

If the second parameter to `truth_tables` is provided, it automatically inserts the sequence of names into the global namespace

### Build truth tables with operator overloading

```python
f = A.ite(B, C ^ D) & E | F
```

The truth table support `|`, `&`, `^`, and `~` for OR, AND, XOR, INVERT, respectively. It also supports `ite` (if-then-else), `iff` (if-and-only-if, or EXOR) and `implies` (logical implication). 

### Output the truth table

```python
print(f)
```

Will print the truth as a prime-irredudant cover, in this case:

```python
A&B&E + ~A&C&~D&E + ~A&~C&D&E + F
```

Or,

```python
print(f.SOP())
```

Resulting in 

```
-----1 1
0-011- 1
0-101- 1
11--1- 1
```

Or 

```python
print(f.isop())
```

Resulting in 

```
[{1, 2, 5}, {3, -4, 5, -1}, {-3, 4, 5, -1}, {6}]
```

All three are the same cover. The first is a human-readable expression. The second is similar to Espresso and BLIF formats, and the third is the list of cubes where negative means negation and the nubmer is the variable number starting from 0.

### Manipulate truth tables

In addition to the above, it supports permuting and negating inputs and the output, generating the list of all NPN-equivalent functions and a few other operations.
