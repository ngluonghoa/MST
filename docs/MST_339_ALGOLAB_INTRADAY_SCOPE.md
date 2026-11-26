# §339 — Private Algolab connected intraday source boundary

A separately versioned one-day stock-intraday envelope for the connected
get_price_history product, with bounded raw VND/start-label metadata and
exact columns. The returned counts are conditional wall-clock geometry only.
M30 and H1 are not equivalent to the inherited session-anchored contract;
the H1 afternoon bucket may combine continuous and auction rows.
Even an observed M5/M15 bucket does not prove complete minute input.
No zero-filling, inferred no-trades, other-provider clock selection, D1/W1
adjustment bridge, H4, native TF qualification, or production release.
Reported metadata and caller capture times are not publisher first-known.
The full response is hashed privately, not a wire hash or issuer signature.
No data fetching, source adapter activation, market records, or credentials
in this PR; fixtures are fictional. Revert the isolated PR to roll back.
