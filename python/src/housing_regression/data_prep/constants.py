"""Domain schema, field taxonomies, and encoding hierarchies for Ames Housing."""

from __future__ import annotations

TARGET_COLUMN: str = "SalePrice"
ID_COLUMN: str = "Id"

# Exactly 15 structural absence fields identified in Phase 2 EDA
STRUCTURAL_ABSENCE_COLUMNS: list[str] = [
    "Alley",
    "PoolQC",
    "Fence",
    "MiscFeature",
    "FireplaceQu",
    "GarageType",
    "GarageYrBlt",
    "GarageFinish",
    "GarageQual",
    "GarageCond",
    "BsmtQual",
    "BsmtCond",
    "BsmtExposure",
    "BsmtFinType1",
    "BsmtFinType2",
]

# Nominal fields with structural absence where 'NA' means 'None' (no feature)
STRUCTURAL_NOMINAL_SENTINELS: dict[str, str] = {
    "Alley": "None",
    "GarageType": "None",
    "MiscFeature": "None",
}

# Ordinal fields mapping (hierarchical score, 0 assigned to documented structural absence)
ORDINAL_LEVELS: dict[str, dict[str, int]] = {
    "ExterQual": {"Po": 1, "Fa": 2, "TA": 3, "Gd": 4, "Ex": 5},
    "ExterCond": {"Po": 1, "Fa": 2, "TA": 3, "Gd": 4, "Ex": 5},
    "BsmtQual": {"None": 0, "Po": 1, "Fa": 2, "TA": 3, "Gd": 4, "Ex": 5},
    "BsmtCond": {"None": 0, "Po": 1, "Fa": 2, "TA": 3, "Gd": 4, "Ex": 5},
    "BsmtExposure": {"None": 0, "No": 1, "Mn": 2, "Av": 3, "Gd": 4},
    "BsmtFinType1": {"None": 0, "Unf": 1, "LwQ": 2, "Rec": 3, "BLQ": 4, "ALQ": 5, "GLQ": 6},
    "BsmtFinType2": {"None": 0, "Unf": 1, "LwQ": 2, "Rec": 3, "BLQ": 4, "ALQ": 5, "GLQ": 6},
    "HeatingQC": {"Po": 1, "Fa": 2, "TA": 3, "Gd": 4, "Ex": 5},
    "KitchenQual": {"Po": 1, "Fa": 2, "TA": 3, "Gd": 4, "Ex": 5},
    "Functional": {
        "Sal": 1,
        "Sev": 2,
        "Maj2": 3,
        "Maj1": 4,
        "Mod": 5,
        "Min2": 6,
        "Min1": 7,
        "Typ": 8,
    },
    "FireplaceQu": {"None": 0, "Po": 1, "Fa": 2, "TA": 3, "Gd": 4, "Ex": 5},
    "GarageFinish": {"None": 0, "Unf": 1, "RFn": 2, "Fin": 3},
    "GarageQual": {"None": 0, "Po": 1, "Fa": 2, "TA": 3, "Gd": 4, "Ex": 5},
    "GarageCond": {"None": 0, "Po": 1, "Fa": 2, "TA": 3, "Gd": 4, "Ex": 5},
    "PavedDrive": {"N": 1, "P": 2, "Y": 3},
    "PoolQC": {"None": 0, "Fa": 1, "TA": 2, "Gd": 3, "Ex": 4},
    "Fence": {"None": 0, "MnWw": 1, "GdWo": 2, "MnPrv": 3, "GdPrv": 4},
    "LotShape": {"IR3": 1, "IR2": 2, "IR1": 3, "Reg": 4},
    "LandSlope": {"Sev": 1, "Mod": 2, "Gtl": 3},
}

ORDINAL_COLUMNS: list[str] = list(ORDINAL_LEVELS.keys())

# Nominal fields to be one-hot encoded; MSSubClass is nominal per Issue #15 requirements
NOMINAL_COLUMNS: list[str] = [
    "MSSubClass",
    "MSZoning",
    "Street",
    "Alley",
    "LandContour",
    "Utilities",
    "LotConfig",
    "Neighborhood",
    "Condition1",
    "Condition2",
    "BldgType",
    "HouseStyle",
    "RoofStyle",
    "RoofMatl",
    "Exterior1st",
    "Exterior2nd",
    "MasVnrType",
    "Foundation",
    "Heating",
    "CentralAir",
    "Electrical",
    "GarageType",
    "MiscFeature",
    "SaleType",
    "SaleCondition",
]

# Numeric continuous and discrete count fields
NUMERIC_COLUMNS: list[str] = [
    "LotFrontage",
    "LotArea",
    "OverallQual",
    "OverallCond",
    "YearBuilt",
    "YearRemodAdd",
    "MasVnrArea",
    "BsmtFinSF1",
    "BsmtFinSF2",
    "BsmtUnfSF",
    "TotalBsmtSF",
    "1stFlrSF",
    "2ndFlrSF",
    "LowQualFinSF",
    "GrLivArea",
    "BsmtFullBath",
    "BsmtHalfBath",
    "FullBath",
    "HalfBath",
    "BedroomAbvGr",
    "KitchenAbvGr",
    "TotRmsAbvGrd",
    "Fireplaces",
    "GarageYrBlt",
    "GarageCars",
    "GarageArea",
    "WoodDeckSF",
    "OpenPorchSF",
    "EnclosedPorch",
    "3SsnPorch",
    "ScreenPorch",
    "PoolArea",
    "MiscVal",
    "MoSold",
    "YrSold",
]

# Physical presence indicator columns
STRUCTURAL_INDICATORS: list[str] = [
    "HasGarage",
    "HasBasement",
    "HasFireplace",
    "HasPool",
    "HasFence",
    "HasAlley",
    "HasMiscFeature",
]

# Explicit missingness indicators for genuine non-structural missing fields
# whose training mode/median coincides with physical absence ('None'/0.0)
GENUINE_MISSING_INDICATORS: list[str] = [
    "MasVnrType_is_missing",
    "MasVnrArea_is_missing",
]

ALL_PREDICTOR_COLUMNS: list[str] = sorted(
    list(set(ORDINAL_COLUMNS + NOMINAL_COLUMNS + NUMERIC_COLUMNS))
)
