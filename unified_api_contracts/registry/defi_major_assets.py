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
    "ETH", "WETH", "STETH", "WSTETH", "CBETH", "WBETH", "RETH", "WEETH", "EETH",
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
        # Solana DEXes
        "ORCA",
        "RAYDIUM",
        "KAMINO",
        # Solana DEX pools (2026-07-20 DeFi catalogue canonicalization)
        "METEORA",
        "LIFINITY",
        "PHOENIX",
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
    "WBETH": "0xa2E3356610840701BDf5611a53974510Ae27E2e1",  # DERIVED ethereum etherscan (wBETH; same on BSC)
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


# TVL-exempt FORCE-INCLUDE governance / forced tokens (IS R2c — instruments-service
# availability-denominator honesty). These protocol-native governance / restaking-
# reward tokens enter the instrument catalogue because a dedicated instruments-service
# governance-token adapter (``reference_data/adapters/defi/eigenlayer.py`` /
# ``ethfi.py`` — each declares a ``_GOVERNANCE_TOKENS`` list of ``token_type ==
# "GOVERNANCE_TOKEN"``) emits them directly, NOT because they crossed a DEX
# liquidity / TVL threshold. Marking them ``force_include`` lets the catalogue (and
# every coverage denominator downstream) distinguish a FORCED inclusion from
# COINCIDENTAL liquidity: a ``UNISWAP_V3-ETHEREUM`` EIGEN/WETH pool is coincidental
# liquidity that happens to contain the token, whereas the ``EIGENLAYER-ETHEREUM``
# EIGEN governance instrument is a forced inclusion we track regardless of TVL.
#
# Keyed by canonical PROTOCOL (the venue prefix left of the ``-<chain>`` suffix), so
# a pool that merely CONTAINS a force-include token is never mis-flagged — only the
# governance-token venue that actually issues it. Extend this map (never a bare
# symbol set) when a new protocol's governance/forced token is wired in the same
# adapter shape. SSOT for the catalogue ``force_include`` column + the
# ``is_defi_force_include`` predicate below.
DEFI_FORCE_INCLUDE_TOKENS: dict[str, frozenset[str]] = {
    "EIGENLAYER": frozenset({"EIGEN"}),
    "ETHERFI": frozenset({"ETHFI"}),
}


def is_defi_force_include(venue: str, base_asset: str) -> bool:
    """Return True when a DeFi catalogue row is a TVL-exempt forced governance token.

    ``venue`` is the catalogue venue in either ``PROTOCOL`` or ``PROTOCOL-CHAIN``
    form (e.g. ``EIGENLAYER-ETHEREUM``); the protocol prefix left of the first
    ``-`` is matched against :data:`DEFI_FORCE_INCLUDE_TOKENS`. ``base_asset`` is
    the token symbol. Both compare case-insensitively.

    A DEX pool that merely CONTAINS EIGEN/ETHFI is NOT force-included: its venue
    protocol (``UNISWAP_V3`` / ``CURVE`` / …) is absent from the map, so coincidental
    liquidity stays distinguishable from a forced governance inclusion. Pure +
    idempotent; a no-op ``False`` for every non-governance-token row and every
    non-DeFi asset group (whose venues never match a DeFi protocol key).
    """
    protocol = (venue or "").strip().upper().split("-", 1)[0]
    forced = DEFI_FORCE_INCLUDE_TOKENS.get(protocol)
    if not forced:
        return False
    return (base_asset or "").strip().upper() in forced


# TVL-exempt FORCE-INCLUDE Raydium pools (2026-07-20 DeFi catalogue
# canonicalization). The Solana DEX-pool relevance filter (URDI dex adapters +
# IS ``filter_defi_instruments_by_relevance``) keeps a Raydium pool only when
# BOTH tokens are in :data:`DEFI_MAJOR_ASSET_SYMBOLS`. That correctly drops the
# long tail, but it also silently dropped a set of very-high-TVL pools whose
# non-major token (XMR, BNB, TRX, XRP, LTC, ZEC, meme/ecosystem tokens, …) is
# not on the major-asset whitelist — pools with tens of millions in TVL that we
# DO want in the tradable/observable universe.
#
# This is the top-32 Raydium pools by TVL from the legacy prod snapshot
# ``gs://market-data-tick-defi-prd-<project>/dex_pools/raydium/SOLANA/
# date=2026-04-14/*.parquet`` (98 pools captured; the top-32 cut is the clean
# TVL >= ~$4.0M slice — the operator-confirmed "32" count, floor $4,005,367
# with a structural gap to the 33rd pool at $3,954,454).
#
# Addresses are LOWERCASED Solana base58 pool ids; the predicate
# :func:`is_defi_force_include_pool` lowercases its input, so a pool whose token
# pair fails the major-asset relevance gate is still kept when its lowercased
# pool address is a member here. SSOT for the catalogue force-include of these
# pools + the IS DEX relevance-filter carve-out.
DEFI_FORCE_INCLUDE_POOLS: frozenset[str] = frozenset(
    {
        "3cig1jsphfwqfwbvpsargvgh1sozy7ikef5m4gbcvxve",  # PRIME/CASH
        "3ucnos4nbumplznwztqghnffgkhermbqavemeeomsuxv",  # WSOL/USDC
        "4usrwhonydfubz1kcupz4xcjeadzqzptby4mzu6wegkm",  # XMR/USDC
        "58oqchx4ywmvkdwllzzbi4chocc2fqcuwbkwmihlyqo2",  # WSOL/USDC
        "5egccjkue42yytzy4qg8qtiouwnh6agtvjunryeqcqv1",  # smole/WSOL
        "6ntgudbjyatkia81aqnsowqszhlurn7tzhsbwv5kbzrv",  # LTC/USDC
        "879f697iudjgmevrkrcnw21fcxiaeljk1ffsw2atebce",  # MEW/WSOL
        "89hdpbfmkmox1w6wvo6dmuviug3con9jjyu9nq3hgai6",  # EURC/USDT
        "8nkmsz1e7vctwtp2pk3u3mlufqnq8vctqediqz2pioyv",  # XMR/USDC
        "8wwcnqdzjcy5pt7akhupafknv2txca9sq6ybkgzlbvdt",  # WSOL/pippin
        "9gb28busn8fyigm1dbstb6cpou9mv5a7co1kbnac5hip",  # USDC/BNB
        "agfnrluscrd2e4nwqxw73hdbsn7ekeub2jhx7tx9ytyc",  # Old Slerf/WSOL
        "amtpriwxrenbohq4cnmbybajm4mcwltbexvew8trhevk",  # BNB/USDC
        "aqagyqsdu853wakhxm79cgndoyhrrwxvyhx6qrdyc1fs",  # WSOL/USD1
        "as5mv3ear4nzpmwxbcsez3adbcaxenq4chdawsvlgkcm",  # USDS/USDC
        "bcddhonby65iduz3ev3c9v5xjnkzyu5e56krfhpbm4t9",  # USD1/USDC
        "bzc9nzfmqkxr6fz1dbph7bdf9broyef6pnzesp7v5iiw",  # WSOL/Fartcoin
        "bztgqeys6exuxicyphecyq7pybqodxqmvkjubp4r8muu",  # USDC/USDT
        "cdjtzehhd3k6exv9ssw3zafbmvwedf6qhngbyrshytuc",  # XMR/USDC
        "d8tchx6wmg9gkkoqabej7r5ftssqexbuntcf2pzc7mfj",  # ZEC/USDC
        "drfmodahqzqsw1azvuc8jes2zrt1snn879auipbalpcn",  # XRP/USDC
        "dsuvc5qf5ljhhv5e2td184ixotsncnwj7i4jja4xsrmt",  # BOME/WSOL
        "ep2ib6dydeeqd8mfe2ezhcxx3kp3k2elkkirfpm5eymx",  # $WIF/WSOL
        "ewivkwntcxupsu6ryd7pfvs7u9yv8nq79tj7xggyprp6",  # USX/USDC
        "fqed3ay883zucgclaubkv56jjbweiyjxpstc84yuxqnd",  # $NAP/WSOL
        "fuemmjepntbzthvsevmdgnfq7ywr8uebzraxjrp46vtf",  # LIKE/WSOL
        "g39wywqukbhk8f2wzzzfx3fcsyg91vccbbr6wevp5axy",  # CRCLx/USDC
        "hhsv4hkx2xgdzevqzhcqsznth4jpcgal8qmrqlsh6en7",  # USDC/LTC
        "hlooxritsiz9ampwkf6wvjpccvvgk1xjdtdxdsacn1re",  # TRX/USDC
        "hpgv2jnzgrgfrzjezgkhgtnegrfahtzcvuk3brftfjwk",  # USDC/TRX
        "j3b6dvhes2y1cbmtvz5tcwxnegsjjdbukxduvdpoqms7",  # WSOL/arc
        "mypzpagsrxm1ndqsjrw9e4nkdetqbz7xdkr2tolwzur",  # HYPE/USDC
    }
)


def is_defi_force_include_pool(pool_address: str) -> bool:
    """Return True when a DeFi DEX pool is a TVL-exempt force-included pool.

    ``pool_address`` is a pool contract / account id (EVM hex or Solana base58);
    it is compared case-insensitively against :data:`DEFI_FORCE_INCLUDE_POOLS`
    (stored lowercased). Used by the IS DEX relevance filter to KEEP a
    high-TVL pool whose token pair would otherwise fail the major-asset gate,
    and by the catalogue builder to stamp the ``force_include`` column honestly.

    Pure + idempotent; a no-op ``False`` for every pool not on the curated
    high-TVL allowlist (and for empty / missing addresses).
    """
    if not pool_address:
        return False
    return pool_address.strip().lower() in DEFI_FORCE_INCLUDE_POOLS
