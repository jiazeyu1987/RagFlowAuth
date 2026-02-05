class DocumentError(Exception):
    """Base class for document domain errors."""


class DocumentNotFound(DocumentError):
    pass


class DocumentPermissionDenied(DocumentError):
    pass


class DocumentSourceError(DocumentError):
    pass

