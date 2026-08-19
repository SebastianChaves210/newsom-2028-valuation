"""Model lanes.

Each lane produces an independent posterior over one leg of the decomposition

    P(president) = P(nominee) x P(wins general | nominee)

as an array of Monte Carlo draws.  Lanes never see each other's output; the
ensemble (ensemble.py) is the only place they are combined, via a
Dirichlet-weighted linear opinion pool so that disagreement between lanes
widens - rather than narrows - the final credible interval.
"""
