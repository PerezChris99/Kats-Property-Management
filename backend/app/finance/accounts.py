"""Conservative Ugandan property-business chart of accounts.

Codes are stable bookkeeping identifiers, not client-approved tax treatment.
An accountant must approve recognition rules and historical opening balances.
"""
DEFAULT_ACCOUNTS = (
    ("CASH_CLEARING", "Cash and mobile/bank receipts awaiting external reconciliation", "ASSET"),
    ("BANK", "Externally reconciled bank funds", "ASSET"),
    ("RENT_RECEIVABLE", "Tenant receivables", "ASSET"),
    ("OTHER_RECEIVABLE", "Other receivables", "ASSET"),
    ("PREPAID_EXPENSE", "Prepaid expenses", "ASSET"),
    ("FIXED_ASSETS", "Property fixed assets", "ASSET"),
    ("ACCOUNTS_PAYABLE", "Vendor and operating payables", "LIABILITY"),
    ("TENANT_ADVANCES", "Rent received before invoice allocation", "LIABILITY"),
    ("TENANT_DEPOSITS", "Tenant security deposit liability", "LIABILITY"),
    ("DEPOSIT_REFUNDS_PAYABLE", "Approved deposit refunds awaiting payout proof", "LIABILITY"),
    ("ACCRUED_EXPENSES", "Accrued expenses", "LIABILITY"),
    ("TAX_PAYABLE", "Tax payable", "LIABILITY"),
    ("OWNER_EQUITY", "Owner's equity", "EQUITY"),
    ("RETAINED_EARNINGS", "Retained earnings", "EQUITY"),
    ("RENTAL_INCOME", "Earned rental income", "REVENUE"),
    ("UTILITY_RECOVERY", "Utilities billed to tenants", "REVENUE"),
    ("LATE_FEES", "Authorized late fees", "REVENUE"),
    ("OTHER_INCOME", "Other property income", "REVENUE"),
    ("REVENUE_CREDITS", "Unallocated credit notes (contra-revenue)", "REVENUE"),
    ("MAINTENANCE_EXPENSE", "Property maintenance", "EXPENSE"),
    ("UTILITY_EXPENSE", "Utilities paid", "EXPENSE"),
    ("MANAGEMENT_FEES", "Management expenses", "EXPENSE"),
    ("INSURANCE_EXPENSE", "Property insurance", "EXPENSE"),
    ("PROPERTY_TAX_EXPENSE", "Property taxation", "EXPENSE"),
    ("OTHER_EXPENSE", "Other approved operating expenses", "EXPENSE"),
)

INVOICE_REVENUE = {
    "RENT": "RENTAL_INCOME",
    "WATER": "UTILITY_RECOVERY",
    "ELECTRICITY": "UTILITY_RECOVERY",
    "GARBAGE": "UTILITY_RECOVERY",
    "PARKING": "OTHER_INCOME",
    "CLEANING": "OTHER_INCOME",
    "DAMAGE": "OTHER_INCOME",
    "LATE_FEE": "LATE_FEES",
    "MISCELLANEOUS": "OTHER_INCOME",
}
EXPENSE_ACCOUNTS = {
    "MAINTENANCE": "MAINTENANCE_EXPENSE",
    "REPAIRS": "MAINTENANCE_EXPENSE",
    "WATER": "UTILITY_EXPENSE",
    "ELECTRICITY": "UTILITY_EXPENSE",
    "UTILITIES": "UTILITY_EXPENSE",
    "MANAGEMENT": "MANAGEMENT_FEES",
    "INSURANCE": "INSURANCE_EXPENSE",
    "PROPERTY_TAX": "PROPERTY_TAX_EXPENSE",
}
