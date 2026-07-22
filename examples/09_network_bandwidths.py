"""Select scalar and adaptive bandwidths for NetworkKDE."""

from pykdex import (
    EpanechnikovKernel,
    NetworkKDE,
    NetworkKNNBandwidth,
    NetworkLeastSquaresCV,
    NetworkLeastSquaresCVBandwidth,
    NetworkLikelihoodCV,
    NetworkLikelihoodCVBandwidth,
    NetworkSelectionCache,
    NetworkWorkspace,
    SpatialEvents,
    build_event_event_distances,
    load_t_junction,
)

dataset = load_t_junction()
network = dataset.network
events = SpatialEvents.from_array(
    [[-0.80, 0.0], [-0.40, 0.0], [0.30, 0.0], [0.0, 0.65]],
    crs=network.crs,
    spatial_unit=network.spatial_unit,
)
workspace = NetworkWorkspace.prepare(
    network,
    events,
    lixel_length=0.05,
    max_snap_distance=0.05,
).with_event_event_distances()

# The public helper preserves explicit self-pairs and duplicate zero distances.
event_distances = build_event_event_distances(network, workspace.events)
print(event_distances.shape, event_distances.n_pairs)

# Direct selector use exposes the complete optimization result and cache.
likelihood_selector = NetworkLikelihoodCV(bounds=(0.2, 1.2), maxiter=30)
likelihood_result = likelihood_selector.select(
    workspace,
    kernel=EpanechnikovKernel(),
    junction_policy="simple",
    directed=False,
)
assert isinstance(likelihood_selector.cache_, NetworkSelectionCache)
print(likelihood_result.bandwidth, likelihood_result.score)

least_squares_selector = NetworkLeastSquaresCV(bounds=(0.3, 1.0), maxiter=30)
least_squares_result = least_squares_selector.select(
    workspace,
    kernel=EpanechnikovKernel(),
    junction_policy="continuous",
    directed=False,
)
print(least_squares_result.bandwidth, least_squares_result.score)

# Estimator wrappers resolve scalar CV bandwidths during fit.
selected = NetworkKDE(
    bandwidth=NetworkLikelihoodCVBandwidth(bounds=(0.2, 1.2), maxiter=30),
    junction_policy="simple",
).fit(workspace)
assert selected.bandwidth_selection_ is not None

selected_lscv = NetworkKDE(
    bandwidth=NetworkLeastSquaresCVBandwidth(bounds=(0.3, 1.0), maxiter=30),
    junction_policy="continuous",
).fit(workspace)
assert selected_lscv.bandwidth_selection_ is not None

# kNN produces one source-centred bandwidth per accepted event.
adaptive = NetworkKDE(
    bandwidth=NetworkKNNBandwidth(k=1, minimum_bandwidth=0.05),
    junction_policy="continuous",
).fit_predict(workspace)
print(adaptive.adaptive, adaptive.bandwidth)
