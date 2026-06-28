"""Market data processing service domain schemas — cross-service data contracts.

Book-microstructure summary columns SSOT: book_summary_spec.BOOK_SUMMARY_COLUMNS
"""

from unified_api_contracts.internal.domain.market_data_processing.book_summary_spec import (
    BOOK_SUMMARY_COLUMN_NAMES,
    BOOK_SUMMARY_COLUMNS,
    BOOK_SUMMARY_COLUMNS_BY_NAME,
    BookColumnGroup,
    BookColumnSpec,
    book_summary_column_names_for_group,
)

__all__ = [
    "BOOK_SUMMARY_COLUMNS",
    "BOOK_SUMMARY_COLUMNS_BY_NAME",
    "BOOK_SUMMARY_COLUMN_NAMES",
    "BookColumnGroup",
    "BookColumnSpec",
    "book_summary_column_names_for_group",
]
