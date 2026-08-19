"""Data collectors.

Every collector is idempotent and append-only: each run writes a dated
snapshot under data/snapshots/<source>/ and never mutates prior snapshots,
so the repository accumulates its own history even for sources that only
expose current values.  Collectors must degrade gracefully: a failed source
logs a warning and returns an empty frame rather than killing the pipeline.
"""
