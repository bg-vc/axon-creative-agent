class AxonCreativeError(Exception):
    """Base error shown to CLI users without a traceback."""


class ConfigurationError(AxonCreativeError):
    """The local environment or command is unsafe or incomplete."""


class WorkflowError(AxonCreativeError):
    """A workflow or manifest is invalid."""


class ComfyUIError(AxonCreativeError):
    """ComfyUI rejected or failed a request."""
