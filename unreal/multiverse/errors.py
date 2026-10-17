"""Errors raised by the multiverse layer."""


class MultiverseError(Exception):
    """Base error for seeds, catalogs, trees, and saves."""


class SeedError(MultiverseError):
    """A seed or a seed source could not be used."""


class QuantumSourceUnavailable(SeedError):
    """The quantum stub has no local provider attached."""


class UnknownChoice(MultiverseError):
    """The choice id is not in the major-choice catalog."""


class UnknownUniverse(MultiverseError):
    """No universe in this tree has that id."""


class SaveError(MultiverseError):
    """A save could not be read or does not match this derivation."""


class CatalogError(MultiverseError):
    """The physics or choice catalog on disk is not usable."""
