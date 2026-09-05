"""
Stand-ins for third-party packages, so the test suite runs anywhere.

The backend needs httpx, pydantic-settings, faster-whisper, webrtcvad and
the LiveKit SDK to actually run, but not one of those is needed to test the
logic that has actually broken in this project: which model id to fall back
to, how a Sarvam response is parsed, where an utterance ends, how many
transcriptions may run at once. Requiring the full install to run the tests
would mean they only get run on one machine, which in practice means they
stop getting run.

So each stub below is installed **only if the real package is missing**. On
a fully installed backend this module does nothing at all, and the same
tests exercise the real imports.

Two deliberate properties:

  * The httpx stub raises on every request. No test is allowed to touch the
    network, and a test that accidentally tries should fail loudly rather
    than hang or, worse, quietly succeed against a live API.
  * The pydantic-settings stub does NOT read backend/.env. Tests then run
    against the defaults in app/config.py rather than against whatever is
    in one developer's .env file — which is exactly what you want, because
    a .env value silently overriding a config.py default is a bug this
    project has already been bitten by.

Usage, before importing anything from app:

    try:
        from tests import stubs
    except ImportError:          # discovered with tests/ as the root dir
        import stubs
    stubs.install()
"""

import os
import sys
import types

_installed = False

# backend/, i.e. the directory that holds app/. Kept as a module constant so
# _ensure_backend_on_path can stay a one-liner.
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ensure_backend_on_path() -> None:
    """
    Make `import app...` work no matter how the tests were started.

    Without this, only one invocation works — `python -m unittest discover -s
    tests -t .` from backend/ — and the two most natural things to try while
    iterating both fail with "No module named 'app'": running a single file
    (`python tests/test_asr_provider.py`, which every test module invites with
    its `unittest.main()` block) and discovering from inside tests/.
    """
    if _BACKEND_DIR not in sys.path:
        sys.path.insert(0, _BACKEND_DIR)


def _missing(name: str) -> bool:
    """True when `name` cannot be imported, so a stub is needed."""
    if name in sys.modules:
        return False
    try:
        __import__(name)
    except ImportError:
        return True
    return False


def _stub_pydantic_settings() -> None:
    if not _missing("pydantic_settings"):
        return
    module = types.ModuleType("pydantic_settings")

    class BaseSettings:
        """
        Every field in app/config.py has a default, and defaults live on the
        class — so plain attribute lookup already returns the right value
        and this needs to do nothing but accept overrides.
        """

        def __init__(self, **overrides):
            for key, value in overrides.items():
                setattr(self, key, value)

    module.BaseSettings = BaseSettings
    module.SettingsConfigDict = lambda **kwargs: dict(kwargs)
    sys.modules["pydantic_settings"] = module


def _stub_httpx() -> None:
    if not _missing("httpx"):
        return
    module = types.ModuleType("httpx")

    class RequestError(Exception):
        pass

    class AsyncClient:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def _refuse(self, *args, **kwargs):
            raise RequestError(
                "httpx is stubbed in the test suite — a test tried to make a real HTTP "
                "request. Patch the method that posts instead."
            )

        post = _refuse
        get = _refuse

    module.RequestError = RequestError
    module.HTTPError = RequestError
    module.AsyncClient = AsyncClient
    sys.modules["httpx"] = module


def _stub_faster_whisper() -> None:
    if not _missing("faster_whisper"):
        return
    module = types.ModuleType("faster_whisper")

    class WhisperModel:
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "faster-whisper is stubbed in the test suite — no test loads a real model "
                "(that is what scripts/preflight.py is for)."
            )

    module.WhisperModel = WhisperModel
    sys.modules["faster_whisper"] = module


def _stub_webrtcvad() -> None:
    if not _missing("webrtcvad"):
        return
    module = types.ModuleType("webrtcvad")

    class Vad:
        """
        Never reports speech. Tests that care about segmentation inject their
        own scripted VAD into ParticipantAudioBuffer, which is why that class
        takes the vad as a constructor argument.
        """

        def __init__(self, aggressiveness: int = 0):
            self.aggressiveness = aggressiveness

        def is_speech(self, frame_bytes: bytes, sample_rate: int) -> bool:
            return False

    module.Vad = Vad
    sys.modules["webrtcvad"] = module


def _stub_livekit() -> None:
    if not _missing("livekit"):
        return

    class _Placeholder:
        """Exists so `track: rtc.Track` annotations resolve at import time."""

        def __init__(self, *args, **kwargs):
            raise RuntimeError("the LiveKit SDK is stubbed in the test suite")

    class TrackKind:
        KIND_AUDIO = "audio"
        KIND_VIDEO = "video"

    package = types.ModuleType("livekit")
    package.__path__ = []  # marks it as a package so submodules can be attached

    rtc = types.ModuleType("livekit.rtc")
    for attribute in ("Room", "Track", "AudioStream", "AudioFrame", "RemoteParticipant",
                      "LocalParticipant", "TrackPublication"):
        setattr(rtc, attribute, type(attribute, (_Placeholder,), {}))
    rtc.TrackKind = TrackKind

    api = types.ModuleType("livekit.api")
    for attribute in ("AccessToken", "VideoGrants", "LiveKitAPI", "RoomServiceClient"):
        setattr(api, attribute, type(attribute, (_Placeholder,), {}))

    package.rtc = rtc
    package.api = api
    sys.modules["livekit"] = package
    sys.modules["livekit.rtc"] = rtc
    sys.modules["livekit.api"] = api


def _stub_mcp() -> None:
    if not _missing("mcp"):
        return
    module = types.ModuleType("mcp")
    module.__path__ = []  # marks it as a package so submodules can be attached

    class ClientSession:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("mcp is stubbed in the test suite — no test talks to the Stitch MCP server")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc_info):
            return False

        async def call_tool(self, *args, **kwargs):
            raise RuntimeError("mcp is stubbed in the test suite")

    module.ClientSession = ClientSession
    sys.modules["mcp"] = module

    client = types.ModuleType("mcp.client")
    client.__path__ = []
    streamable = types.ModuleType("mcp.client.streamable_http")
    streamable.streamablehttp_client = lambda url: None
    client.streamable_http = streamable
    sys.modules["mcp.client"] = client
    sys.modules["mcp.client.streamable_http"] = streamable


def install() -> None:
    """Idempotent — safe to call from every test module."""
    global _installed
    if _installed:
        return
    _installed = True
    _ensure_backend_on_path()
    _stub_pydantic_settings()
    _stub_httpx()
    _stub_faster_whisper()
    _stub_webrtcvad()
    _stub_livekit()
    _stub_mcp()
