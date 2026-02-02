# SymPy Verification Checklist

Use symbolic checks to reduce algebra/calculus errors.

## Common checks
- Equality check (simplify difference to 0)
- Derivative/integral confirmation
- Solve/verify roots or stationary points
- Series expansion near boundary points

## Minimal snippet template

```python
import sympy as sp

# Define symbols with assumptions when needed
x = sp.Symbol("x", real=True)

# expr_left = ...
# expr_right = ...

check = sp.simplify(expr_left - expr_right)
print(check)  # Expect 0 when identities hold under assumptions
```

