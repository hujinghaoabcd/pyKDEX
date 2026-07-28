# pyKDEX

pyKDEX is a composition-oriented framework for kernel density and event
intensity estimation in Euclidean space, time, linear networks, and their
combinations.

The current package provides rigorously tested spatial KDE, ordinary
spatiotemporal KDE, radial and heat-equation network KDE, and adaptive
temporal-network KDE on measured lixel-by-time support.

Prepared network and network-time workspaces can be persisted as checksummed,
versioned local archives or directories without pickle.

Version 0.0.15 adds exposure fields, exposure-adjusted event rates, and
shared-fixed-bandwidth case-control relative risk on measured spatial, network,
space-time, and network-time supports. Zero denominators require an explicit
policy and no hidden epsilon or pseudocount is introduced.
