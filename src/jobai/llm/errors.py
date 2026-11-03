class LLMError(Exception):
    pass


class SpendCapExceeded(LLMError):
    pass


class KillSwitchActive(LLMError):
    pass


class LadderExhausted(LLMError):
    pass


class ProviderError(LLMError):
    pass


class ProviderTimeout(ProviderError):
    """Request timed out; the provider may still bill it, so callers charge worst case."""


class LLMParseError(LLMError):
    """Provider output was not valid JSON for a structured-output call."""
