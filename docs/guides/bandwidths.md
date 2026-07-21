# Bandwidths

The first baseline exposes `FixedBandwidth`. The strategy interface already
accepts a future vector of event-specific bandwidths, allowing Abramson, kNN,
and balloon strategies without changing estimator evaluation code.
