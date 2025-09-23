from typing import Union


class ValidationUtils:
    @staticmethod
    def validate_symbol(symbol: str) -> str:
        if not isinstance(symbol, str) or not symbol.strip():
            return "Invalid symbol"
        return ""

    @staticmethod
    def validate_quantity(quantity: Union[int, float]) -> str:
        if not isinstance(quantity, (int, float)) or quantity == 0:
            return "Quantity must be a non-zero number"
        return ""

    @staticmethod
    def validate_positive_number(value: Union[int, float], field_name: str) -> str:
        if not isinstance(value, (int, float)) or value <= 0:
            return f"{field_name} must be a positive number"
        return ""

    @staticmethod
    def validate_option_params(symbol: str, quantity: Union[int, float], stop_price: Union[int, float], profit_price: Union[int, float]) -> str:
        errors = []
        if error := ValidationUtils.validate_symbol(symbol):
            errors.append(error)
        if error := ValidationUtils.validate_quantity(quantity):
            errors.append(error)
        if error := ValidationUtils.validate_positive_number(stop_price, "stop_price"):
            errors.append(error)
        if error := ValidationUtils.validate_positive_number(profit_price, "profit_price"):
            errors.append(error)
        return "; ".join(errors) if errors else ""