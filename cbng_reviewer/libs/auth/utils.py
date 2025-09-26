from typing import Optional

from cbng_reviewer.libs.wikipedia.reader import WikipediaReader
from cbng_reviewer.models import User


def create_user(
    username: str, require_central_id: bool = True, grant_reviewer_rights: bool = False, auto_grant_rights: bool = True
) -> Optional[User]:
    central_user = WikipediaReader().get_central_user(username=username)
    if not central_user and require_central_id:
        return None

    user, _ = User.objects.get_or_create(username=username)
    if central_user:
        user.central_user_id = central_user.id

    if grant_reviewer_rights:
        user.is_reviewer = True
        user.save()
    elif auto_grant_rights:
        from cbng_reviewer.libs.auth.rights import AutoReviewerRightsChecker

        # Note: notify IRC but not the user - this is an admin flow, so assume discussion is happening elsewhere
        AutoReviewerRightsChecker().execute(user, notify_user=False)
    return user
