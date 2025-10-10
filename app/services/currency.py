CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "THB": "฿",
    # Add other currencies as needed
}

def get_currency_symbol(currency_code: str) -> str:
    """Returns the currency symbol for a given currency code."""
    return CURRENCY_SYMBOLS.get(currency_code.upper(), "")
