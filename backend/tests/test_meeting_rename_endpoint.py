"""
The host's "rename a meeting" endpoint (Meeting History → pencil icon).

Every meeting starts life as "Untitled Meeting" (or a create-time name), and
the history list is unreadable if they all look alike. This endpoint lets the
host give it a real title afterwards. Host-only is enforced one layer up by the
require_meeting_host dependency (covered by the meeting-auth tests); here we
drive rename_meeting directly with a hand-built MeetingSession so nothing needs
a request, a cookie, or the network.

It also checks the persistence hook: a store-backed session must write the new
name through to the store, because that's what survives a process restart.

Run from the backend/ directory:
    python -m unittest tests.test_meeting_rename_endpoint -v
"""

import unittest

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

from fastapi import HTTPException  # noqa: E402

from app.api.meetings import RenameMeetingRequest, rename_meeting  # noqa: E402
from app.meetings.session import MeetingSession  # noqa: E402


class _RecordingStore:
    """Minimal store that only records what rename would persist. Matches the
    duck-typed hook MeetingSession.rename calls (update_meeting_name)."""

    def __init__(self):
        self.renames = []

    def update_meeting_name(self, meeting_id, new_name):
        self.renames.append((meeting_id, new_name))


class RenameMeetingEndpointTest(unittest.IsolatedAsyncioTestCase):
    def _session(self) -> MeetingSession:
        return MeetingSession(meeting_id="m-rename", name="Untitled Meeting", host_user_id="u1")

    async def test_rename_changes_the_name(self):
        s = self._session()
        result = await rename_meeting(RenameMeetingRequest(name="Restaurant app kickoff"), session=s)

        self.assertEqual(s.name, "Restaurant app kickoff")
        self.assertEqual(result["name"], "Restaurant app kickoff")
        self.assertEqual(result["meeting_id"], "m-rename")

    async def test_leading_trailing_space_is_trimmed(self):
        s = self._session()
        result = await rename_meeting(RenameMeetingRequest(name="  Trading dashboard  "), session=s)
        self.assertEqual(s.name, "Trading dashboard")
        self.assertEqual(result["name"], "Trading dashboard")

    async def test_a_blank_name_is_rejected_with_400(self):
        s = self._session()
        with self.assertRaises(HTTPException) as ctx:
            await rename_meeting(RenameMeetingRequest(name="   "), session=s)
        self.assertEqual(ctx.exception.status_code, 400)
        # The old name must survive a rejected rename.
        self.assertEqual(s.name, "Untitled Meeting")

    async def test_rename_persists_through_the_store(self):
        store = _RecordingStore()
        s = MeetingSession(meeting_id="m-rename", name="Untitled Meeting", host_user_id="u1")
        s._store = store

        await rename_meeting(RenameMeetingRequest(name="Fitness tracker"), session=s)

        self.assertEqual(store.renames, [("m-rename", "Fitness tracker")])

    async def test_rejected_rename_is_not_persisted(self):
        store = _RecordingStore()
        s = MeetingSession(meeting_id="m-rename", name="Untitled Meeting", host_user_id="u1")
        s._store = store

        with self.assertRaises(HTTPException):
            await rename_meeting(RenameMeetingRequest(name="  "), session=s)

        self.assertEqual(store.renames, [], "a blank rename must not touch the store")


if __name__ == "__main__":
    unittest.main(verbosity=2)
