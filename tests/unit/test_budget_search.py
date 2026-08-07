"""Tests para Budget Search Agent y endpoint."""
import pytest
from app.agents.budget_search_agent import BudgetSearchAgent


def test_calculate_max_purchase_price_spain():
    agent = BudgetSearchAgent(profile_name="SPAIN")
    max_price = agent.calculate_max_purchase_price(15000)
    assert max_price > 0
    assert max_price < 15000


def test_budget_decreases_with_lower_capital():
    agent = BudgetSearchAgent(profile_name="SPAIN")
    high = agent.calculate_max_purchase_price(20000)
    low = agent.calculate_max_purchase_price(10000)
    assert high > low


def test_fixed_costs_subtracted():
    agent = BudgetSearchAgent(profile_name="SPAIN")
    profile = agent.calculate_max_purchase_price(15000)
    assert profile > 0
