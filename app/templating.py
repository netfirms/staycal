from fastapi.templating import Jinja2Templates
from .services.currency import get_currency_symbol

def currency_symbol_filter(currency_code: str) -> str:
    """A Jinja2 filter to get the currency symbol for a given currency code."""
    return get_currency_symbol(currency_code)

# Create a single, shared Jinja2Templates instance
templates = Jinja2Templates(directory="app/templates")
# Add the custom filter to the environment
templates.env.filters["currency_symbol"] = currency_symbol_filter
