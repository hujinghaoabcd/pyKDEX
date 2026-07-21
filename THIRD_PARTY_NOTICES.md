# Third-party notices and implementation independence

pyKDEX is independently implemented. Runtime estimation code does not import or
call spNetwork, spatstat, PyNKDV, SANET, or other external KDE implementations.

Published methods and external software may be used during development to:

- understand mathematical definitions;
- generate one-time independent numerical reference fixtures;
- compare accuracy, mass conservation, and computational behaviour.

External source code must not be copied into pyKDEX unless its licence is
compatible, attribution is complete, and the contribution is explicitly
reviewed. GPL-licensed implementations are research references only and are
not source-code donors for this MIT-licensed package.
