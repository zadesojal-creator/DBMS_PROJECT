"""
Indian Number Formatting & Currency Utilities (utils/formatters.py)
Formats numbers using standard Indian grouping (Lakhs and Crores: 1,00,000.00).
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Union

def format_inr(
    value: Union[Decimal, float, int, str, None],
    decimals: int = 2,
    symbol: bool = True
) -> str:
    """
    Formats a numeric value into the Indian currency system (₹ 1,00,000.00).
    Negative numbers: -₹ 1,00,000.00 or -₹1,00,000.00
    """
    if value is None:
        return "—"

    try:
        if isinstance(value, float):
            d = Decimal(str(value))
        elif isinstance(value, Decimal):
            d = value
        else:
            d = Decimal(str(value).strip().replace(',', ''))
    except Exception:
        return "—"

    is_negative = d < 0
    d = abs(d)

    # Quantize to target decimals
    fmt_str = '1.' + ('0' * decimals) if decimals > 0 else '1'
    d_quantized = d.quantize(Decimal(fmt_str), rounding=ROUND_HALF_UP)
    
    parts = str(d_quantized).split('.')
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else ""

    if len(integer_part) <= 3:
        grouped = integer_part
    else:
        last_three = integer_part[-3:]
        remaining = integer_part[:-3]
        # Group remaining into pairs of 2 from right to left
        groups = []
        while len(remaining) > 2:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        if remaining:
            groups.insert(0, remaining)
        grouped = ",".join(groups) + "," + last_three

    result = grouped
    if decimals > 0 and decimal_part:
        result += "." + decimal_part

    sym = "₹ " if symbol else ""
    if is_negative:
        return f"-{sym}{result}"
    return f"{sym}{result}"

def format_pct(value: Union[Decimal, float, int, None], sign: bool = True) -> str:
    """Formats percentage change with arrow/sign (+1.25%, -0.40%)."""
    if value is None:
        return "—"
    try:
        val = float(value)
    except Exception:
        return "—"
    prefix = "+" if sign and val > 0 else ""
    return f"{prefix}{val:.2f}%"

def format_qty(value: Union[int, None]) -> str:
    """Formats share quantities with Indian comma separation."""
    if value is None:
        return "0"
    return format_inr(value, decimals=0, symbol=False)
