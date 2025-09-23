from typing import List
from .models import FinancialDataPoint


class DataProcessor:
    def calculate_moving_average(self, data: List[FinancialDataPoint], periods: int) -> float:
        if len(data) >= periods:
            relevant_data = data[-periods:]
            sum_of_data = sum(data_point.close for data_point in relevant_data)
            return sum_of_data / periods
        return data[-1].close if data else 0.0

    def calculate_relative_strength_index(self, data: List[FinancialDataPoint], periods: int) -> float:
        relevant_data = data[-periods:]
        gains = []
        losses = []
        for i in range(1, len(relevant_data)):
            change = relevant_data[i].close - relevant_data[i - 1].close
            if change > 0:
                gains.append(change)
            else:
                losses.append(abs(change))
        num_periods = len(relevant_data) - 1
        if num_periods == 0:
            return 50.0
        avg_gain = sum(gains) / num_periods
        avg_loss = sum(losses) / num_periods
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
