"""DeFi venue contracts: blockchain and decentralized venues."""

from __future__ import annotations

__api_version__ = "v1"  # matches provider_api_versions.yaml


from typing import TypedDict


class VenueContract(TypedDict):
    """Per-venue contract claims."""

    has_rest: bool
    has_websocket: bool
    has_fix: bool
    """Config field name for Secret Manager (UnifiedCloudConfig), or empty if no API key."""
    config_secret_field: str
    """Expected schema class names in this venue's schemas.py (REST response types)."""
    response_schema_classes: list[str]
    """Expected error/status schema class names."""
    error_schema_classes: list[str]
    """Example file name pattern -> schema class name for validation."""
    example_schema_map: dict[str, str]


DEFI_VENUES: dict[str, VenueContract] = {
    "thegraph": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "thegraph_secret_name",
        "response_schema_classes": [
            "TheGraphResponse",
            "SubgraphPool",
            "SubgraphSwap",
            "SubgraphToken",
            "SubgraphReserve",
            "SubgraphAaveUserPosition",
            "SubgraphUniV3Position",
            "SubgraphUniV3PoolTick",
            "SubgraphCurveGauge",
            "SubgraphCurveVotingEscrow",
            "SubgraphMorphoPosition",
            "SubgraphLidoRebase",
            "SubgraphEthenaYield",
            "SubgraphERC20Transfer",
            "SubgraphERC20Approval",
        ],
        "error_schema_classes": ["GraphQLError"],
        "example_schema_map": {
            "response_example.json": "TheGraphResponse",
            "graphql_error_example.json": "GraphQLError",
        },
    },
    "alchemy": {
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "alchemy_secret_name",
        "response_schema_classes": [
            "AlchemyRpcResponse",
            "AlchemyAssetTransfer",
            "AlchemyTokenBalance",
            "AlchemyBlock",
            "AlchemyTransaction",
            "AlchemyTransactionReceipt",
            "AlchemyLog",
            "AlchemyDecodedLog",
            "AlchemyGasOracle",
            "AlchemyEnsResolution",
            "AlchemyNFTMetadata",
            "AlchemyNFTOwnership",
            "AlchemyTokenMetadata",
            "AlchemySimulationResult",
            "AlchemyWebhookSubscription",
        ],
        "error_schema_classes": ["AlchemyError"],
        "example_schema_map": {
            "rpc_response_example.json": "AlchemyRpcResponse",
            "error_example.json": "AlchemyError",
        },
    },
    "bloxroute": {
        "has_rest": True,
        "has_websocket": True,
        "has_fix": False,
        "config_secret_field": "bloxroute_secret_name",
        "response_schema_classes": [
            "BloxrouteTxSubmitParams",
            "BloxrouteTxSubmitResult",
            "BloxrouteJsonRpcResponse",
            "BloxrouteBdnBlocksParams",
            "BloxrouteSubscribeParams",
            "BloxrouteProtectEndpoints",
        ],
        "error_schema_classes": ["BloxrouteError"],
        "example_schema_map": {"error_example.json": "BloxrouteError"},
    },
}
