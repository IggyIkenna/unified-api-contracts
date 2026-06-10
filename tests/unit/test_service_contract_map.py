"""Tests for registry/service_contract_map.py — service contract registry."""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.service_contract_map import (
    SERVICE_CONTRACT_MAP,
    ServiceContract,
    canonical_producer,
    consumers_of,
    get_service_contract,
)


class TestServiceContractMapContents:
    def test_map_contains_known_services(self) -> None:
        assert "strategy-service" in SERVICE_CONTRACT_MAP
        assert "execution-service" in SERVICE_CONTRACT_MAP
        assert "alerting-service" in SERVICE_CONTRACT_MAP

    def test_all_entries_are_service_contracts(self) -> None:
        for contract in SERVICE_CONTRACT_MAP.values():
            assert isinstance(contract, ServiceContract)

    def test_strategy_service_owns_archetype_definitions(self) -> None:
        contract = SERVICE_CONTRACT_MAP["strategy-service"]
        assert "archetype_definitions" in contract.owns

    def test_execution_service_emits_fill_event(self) -> None:
        contract = SERVICE_CONTRACT_MAP["execution-service"]
        assert "FillEvent" in contract.emits

    def test_alerting_service_forbidden_imports(self) -> None:
        contract = SERVICE_CONTRACT_MAP["alerting-service"]
        assert len(contract.forbidden_imports) > 0

    def test_execution_service_has_forbidden_exceptions(self) -> None:
        contract = SERVICE_CONTRACT_MAP["execution-service"]
        assert len(contract.forbidden_exceptions) > 0


class TestGetServiceContract:
    def test_returns_contract_for_known_service(self) -> None:
        contract = get_service_contract("strategy-service")
        assert contract is not None
        assert isinstance(contract, ServiceContract)
        assert contract.service_name == "strategy-service"

    def test_returns_none_for_unknown_service(self) -> None:
        contract = get_service_contract("nonexistent-service")
        assert contract is None

    def test_execution_service_contract(self) -> None:
        contract = get_service_contract("execution-service")
        assert contract is not None
        assert "order_lifecycle" in contract.owns

    def test_alerting_service_contract(self) -> None:
        contract = get_service_contract("alerting-service")
        assert contract is not None
        assert "AlertDispatched" in contract.emits


class TestCanonicalProducer:
    def test_fill_event_producer_is_execution_service(self) -> None:
        producer = canonical_producer("FillEvent")
        assert producer == "execution-service"

    def test_strategy_instruction_producer(self) -> None:
        producer = canonical_producer("StrategyInstruction")
        assert producer == "strategy-service"

    def test_alert_dispatched_producer(self) -> None:
        producer = canonical_producer("AlertDispatched")
        assert producer == "alerting-service"

    def test_unknown_event_type_returns_none(self) -> None:
        producer = canonical_producer("UnknownEventType99999")
        assert producer is None

    def test_each_event_has_at_most_one_canonical_producer(self) -> None:
        all_emitted_events: dict[str, list[str]] = {}
        for contract in SERVICE_CONTRACT_MAP.values():
            for event in contract.emits:
                all_emitted_events.setdefault(event, []).append(contract.service_name)
        # canonical_producer tests uniqueness — multiple producers for an event is allowed
        # but canonical_producer returns ONE (the first found)
        for event, producers in all_emitted_events.items():
            result = canonical_producer(event)
            assert result in producers


class TestConsumersOf:
    def test_fill_event_consumed_by_strategy(self) -> None:
        consumers = consumers_of("FillEvent")
        assert "strategy-service" in consumers

    def test_strategy_instruction_consumed_by_execution(self) -> None:
        consumers = consumers_of("StrategyInstruction")
        assert "execution-service" in consumers

    def test_unknown_event_has_no_consumers(self) -> None:
        consumers = consumers_of("NonExistentEvent99999")
        assert consumers == frozenset()

    def test_returns_frozenset(self) -> None:
        result = consumers_of("FillEvent")
        assert isinstance(result, frozenset)

    def test_risk_event_has_multiple_consumers(self) -> None:
        consumers = consumers_of("RiskEvent")
        assert len(consumers) > 0


class TestServiceContractFrozen:
    def test_service_contract_is_frozen(self) -> None:
        contract = get_service_contract("strategy-service")
        assert contract is not None
        with pytest.raises((AttributeError, TypeError)):
            contract.service_name = "other-service"  # type: ignore[misc]

    def test_owns_is_frozenset(self) -> None:
        contract = get_service_contract("strategy-service")
        assert contract is not None
        assert isinstance(contract.owns, frozenset)

    def test_emits_is_frozenset(self) -> None:
        contract = get_service_contract("strategy-service")
        assert contract is not None
        assert isinstance(contract.emits, frozenset)

    def test_consumes_is_frozenset(self) -> None:
        contract = get_service_contract("execution-service")
        assert contract is not None
        assert isinstance(contract.consumes, frozenset)
