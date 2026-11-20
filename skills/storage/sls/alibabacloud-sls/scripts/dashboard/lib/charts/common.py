"""Shared reducer choices for chart bindings."""

POSITION_REDUCERS = {"first", "firstNotNull", "last", "lastNotNull"}

NUMERIC_REDUCERS = {
    "min",
    "max",
    "mean",
    "minAboveZero",
    "range",
    "total",
    "step",
    "changeCount",
    "count",
    "difference",
    "differencePercent",
    "distinctCount",
}

REDUCERS = POSITION_REDUCERS | NUMERIC_REDUCERS
