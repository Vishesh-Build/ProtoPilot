"""
The host's manual "add a requirement" endpoint.

Mid-meeting, someone points out a requirement that was missed — often after
the prototype is already built. The transcription extractor usually catches
it, but the host shouldn't have to gamble on that during a live demo. This
endpoint adds it as *approved*, so the next "Regenerate" folds it in with no
extra click, and refuses a near-duplicate rather than silently dropping it.

The endpoint is driven directly with a hand-built MeetingSession in place of
the host-auth dependency, so nothing here needs a request, a cookie, or the
network.

Run from the backend/ directory:
    python -m unittest tests.test_requirement_add_endpoint -v
"""

import unittest

try:
    from tests import stubs
except ImportError:  # discovered with tests/ as the root dir
    import stubs
stubs.install()

from fastapi import HTTPException  # noqa: E402

from app.api.requirements import RequirementCreate, add_requirement  # noqa: E402
from app.meetings.session import MeetingSession  # noqa: E402


class AddRequirementEndpointTest(unittest.IsolatedAsyncioTestCase):
    def _session(self) -> MeetingSession:
        return MeetingSession(meeting_id="m-add", host_user_id="u1")

    async def test_manual_add_is_stored_as_approved(self):
        s = self._session()
        result = await add_requirement("m-add", RequirementCreate(title="Export to PDF"), session=s)

        self.assertEqual(result["requirement"]["status"], "approved")
        self.assertEqual(len(s.requirements), 1)
        self.assertEqual(s.requirements[0].status, "approved")
        self.assertEqual(s.requirements[0].title, "Export to PDF")

    async def test_added_requirement_lands_in_the_set_generation_runs_on(self):
        # "approved" is exactly the filter the generate socket applies, so an
        # added requirement is picked up by the very next Regenerate.
        s = self._session()
        await add_requirement("m-add", RequirementCreate(title="Push notifications"), session=s)

        approved = [r.title for r in s.requirements if r.status == "approved"]
        self.assertEqual(approved, ["Push notifications"])

    async def test_leading_trailing_space_is_trimmed(self):
        s = self._session()
        result = await add_requirement("m-add", RequirementCreate(title="  Search bar  "), session=s)
        self.assertEqual(result["requirement"]["title"], "Search bar")

    async def test_a_near_duplicate_is_rejected_with_409(self):
        s = self._session()
        await add_requirement("m-add", RequirementCreate(title="Login screen"), session=s)

        with self.assertRaises(HTTPException) as ctx:
            # Same requirement, reworded whitespace/case — the dedup net catches it.
            await add_requirement("m-add", RequirementCreate(title="login  screen"), session=s)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(len(s.requirements), 1, "the duplicate must not be added")

    async def test_a_blank_title_is_rejected_with_422(self):
        s = self._session()
        with self.assertRaises(HTTPException) as ctx:
            await add_requirement("m-add", RequirementCreate(title="   "), session=s)
        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(len(s.requirements), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
