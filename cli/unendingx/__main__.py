"""Allow: python -m unendingx"""
try:
    from .cli import main
except ImportError:
    from cli import main
