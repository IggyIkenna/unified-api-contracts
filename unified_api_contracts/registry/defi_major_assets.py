"""DeFi major asset symbols — SSOT for instrument relevance filtering.

Used by URDI DEX adapters to filter pools at query time (only return pools
where both base AND quote are in this set for DEXes, or base for lending).

This is the canonical default. instruments-service config_reloaders can
override via cloud ConfigStore (hot-reloadable), but URDI adapters use this
as the built-in filter so they never return irrelevant instruments.

Mirrors UCI InstrumentDomainConfig.defi_major_assets default — kept in sync
manually. If you add an asset here, add it to UCI too.
"""

from __future__ import annotations

# fmt: off
DEFI_MAJOR_ASSET_SYMBOLS: frozenset[str] = frozenset({
    # ETH and liquid staking/restaking derivatives
    "ETH", "WETH", "STETH", "WSTETH", "CBETH", "RETH", "WEETH", "EETH",
    "SFRXETH", "FRXETH", "OETH", "OSETH", "SWETH", "ETHX", "METH",
    "EZETH", "RSETH", "PUFETH", "ANKRETH",
    # BTC and wrapped variants
    "BTC", "WBTC", "TBTC", "CBBTC", "LBTC",
    # Major stablecoins
    "USDT", "USDC", "DAI", "FRAX", "USDE", "SUSDE", "GHO", "CRVUSD",
    "LUSD", "PYUSD", "EURC", "SUSD", "TUSD", "USDP",
    # Major DeFi governance / Aave collateral
    "AAVE", "LINK", "UNI", "MKR", "CRV", "SNX", "BAL", "LDO", "RPL",
    "COMP", "YFI", "SUSHI", "1INCH", "FXS",
    # EigenLayer + EtherFi governance tokens (reward tokens for restaking)
    "EIGEN", "ETHFI",
    # Other liquid assets on Aave / multi-chain
    "SOL", "MATIC", "WMATIC", "AVAX", "WAVAX", "BNB", "WBNB",
    # Solana liquid staking + top ecosystem tokens
    "WSOL", "MSOL", "STSOL", "JITOSOL", "BSOL", "JSOL",
    "JUP", "RAY", "ORCA", "BONK", "PYTH", "JTO", "WIF", "HNT",
    "MNDE",  # Marinade governance (LP pairs)
    # Solana extended major assets (high liquidity on Raydium/Orca)
    "RNDR", "W", "TENSOR", "KMNO", "DRIFT", "MOBILE", "IOT",
    "SAMO", "FIDA", "SRM", "STEP", "ATLAS", "POLIS", "MEAN",
    "RENDER", "POPCAT", "MEW",
    # Bridging tokens (cross-chain standards)
    "WETH.E", "USDC.E", "USDT.E",  # Avalanche/Polygon bridged variants
})
# fmt: on

# DEX keyword detection — venues containing these are treated as DEX pools
# where BOTH base and quote must be in the whitelist.
# Must cover all DEX protocols in PROTOCOL_CAPABILITIES with protocol_class=DEX.
DEX_VENUE_KEYWORDS: frozenset[str] = frozenset(
    {
        # EVM DEXes
        "UNISWAP",
        "BALANCER",
        "CURVE",
        "PANCAKESWAP",
        "SUSHISWAP",
        "AERODROME",
        "CAMELOT",
        "VELODROME",
        "TRADERJOE",
        "GMX",
        # Solana DEXes
        "ORCA",
        "RAYDIUM",
        "KAMINO",
    }
)

# Ethereum mainnet contract addresses for GraphQL token-address filtering.
# Used by Uniswap V2/V3/V4, Balancer, Curve subgraph queries to filter pools
# at the query level (where: { token0_in: [...] }) instead of client-side.
# fmt: off
DEFI_MAJOR_ASSET_ADDRESSES: dict[str, str] = {
    # ETH and wrapped
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # DERIVED ethereum etherscan
    # BTC wrapped
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # DERIVED ethereum etherscan
    "TBTC": "0x18084fbA666a33d37592fA2633fD49a74DD93a88",  # DERIVED ethereum etherscan
    "CBBTC": "0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf",  # DERIVED ethereum etherscan
    # Major stablecoins
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # DERIVED ethereum etherscan
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # DERIVED ethereum etherscan
    "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",  # DERIVED ethereum etherscan
    "FRAX": "0x853d955aCEf822Db058eb8505911ED77F175b99e",  # DERIVED ethereum etherscan
    "USDE": "0x4c9EDD5852cd905f086C759E8383e09bff1E68B3",  # DERIVED ethereum etherscan
    "SUSDE": "0x9D39A5DE30e57443BfF2A8307A4256c8797A3497",  # DERIVED ethereum etherscan
    "GHO": "0x40D16FC0246aD3160Ccc09B8D0D3A2cD28aE6C2f",  # DERIVED ethereum etherscan
    "CRVUSD": "0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E",  # DERIVED ethereum etherscan
    "LUSD": "0x5f98805A4E8be255a32880FDeC7F6728C6568bA0",  # DERIVED ethereum etherscan
    "PYUSD": "0x6c3ea9036406852006290770BEdFcAbA0e23A0e8",  # DERIVED ethereum etherscan
    "EURC": "0x1aBaEA1f7C830bD89Acc67eC4af516284b1bC33c",  # DERIVED ethereum etherscan
    # Liquid staking derivatives
    "STETH": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",  # DERIVED ethereum etherscan
    "WSTETH": "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0",  # DERIVED ethereum etherscan
    "CBETH": "0xBe9895146f7AF43049ca1c1AE358B0541Ea49704",  # DERIVED ethereum etherscan
    "RETH": "0xae78736Cd615f374D3085123A210448E74Fc6393",  # DERIVED ethereum etherscan
    "WEETH": "0xCd5fE23C85820F7B72D0926FC9b05b43E359b7ee",  # DERIVED ethereum etherscan
    "SFRXETH": "0xac3E018457B222d93114458476f3E3416Abbe38F",  # DERIVED ethereum etherscan
    "FRXETH": "0x5E8422345238F34275888049021821E8E08CAa1f",  # DERIVED ethereum etherscan
    "EZETH": "0xbf5495Efe5DB9ce00f80364C8B423567e58d2110",  # DERIVED ethereum etherscan
    "RSETH": "0xA1290d69c65A6Fe4DF752f95823fAe25cB99e5A7",  # DERIVED ethereum etherscan
    "METH": "0xd5F7838F5C461fefF7FE49ea5ebaF7728bB0ADfa",  # DERIVED ethereum etherscan
    # DeFi governance / Aave collateral
    "AAVE": "0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9",  # DERIVED ethereum etherscan
    "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",  # DERIVED ethereum etherscan
    "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",  # DERIVED ethereum etherscan
    "MKR": "0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",  # DERIVED ethereum etherscan
    "CRV": "0xD533a949740bb3306d119CC777fa900bA034cd52",  # DERIVED ethereum etherscan
    "SNX": "0xC011a73ee8576Fb46F5E1c5751cA3B9Fe0af2a6F",  # DERIVED ethereum etherscan
    "BAL": "0xba100000625a3754423978a60c9317c58a424e3D",  # DERIVED ethereum etherscan
    "LDO": "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32",  # DERIVED ethereum etherscan
    "RPL": "0xD33526068D116cE69F19A9ee46F0bd304F21A51f",  # DERIVED ethereum etherscan
    "COMP": "0xc00e94Cb662C3520282E6f5717214004A7f26888",  # DERIVED ethereum etherscan
    "1INCH": "0x111111111117dC0aa78b770fA6A738034120C302",  # DERIVED ethereum etherscan
    "FXS": "0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0",  # DERIVED ethereum etherscan
    # EigenLayer + EtherFi governance tokens (reward tokens for restaking)
    "EIGEN": "0xec53bF9167f50cDEB3Ae105f56099aaaB9061F83",  # DERIVED ethereum etherscan
    "ETHFI": "0xFe0c30065B384F05761f15d0CC899D4F9F9Cc0eB",  # DERIVED ethereum etherscan
}
# fmt: on

# Flat list of all addresses for GraphQL where-in clauses
DEFI_MAJOR_ASSET_ADDRESS_LIST: list[str] = sorted(DEFI_MAJOR_ASSET_ADDRESSES.values())
