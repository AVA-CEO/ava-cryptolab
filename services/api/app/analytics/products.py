"""Explicit opt-in dispatch; existing journal handlers are not rerouted."""

from app.analytics.cfd import calculate_cfd
from app.schemas.cfd_results import CalculationUnavailable


def calculate_product(product, payload):
    if product == "cfd":
        return calculate_cfd(payload)
    if product in ("crypto_spot", "crypto_linear_futures"):
        # Lazy import: the pure CFD path does not load ORM or database settings.
        from app.analytics.trades import calculate
        from app.models import Trade

        expected_market = "spot" if product == "crypto_spot" else "futures"
        if isinstance(payload, Trade) and payload.market == expected_market:
            return calculate(payload)  # Preserve the established dict/crypto semantics.
        return CalculationUnavailable(
            engine="product-dispatch-v1",
            reason_code="invalid_input",
            message=(
                "Crypto dispatch requires an existing matching legacy crypto Trade, "
                "not CFD lots or an unvalidated dictionary."
            ),
        )
    return CalculationUnavailable(
        engine="product-dispatch-v1",
        reason_code="unsupported_product",
        message="This product has no explicitly supported calculation engine.",
    )
