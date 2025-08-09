-- Minimal data used in testGetUserEditCount
INSERT INTO actor (
    actor_id, actor_user, actor_name
) VALUES (
    70464, 2720564, CAST('Example User' as binary)
);

INSERT INTO revision_userindex (
    rev_id, rev_page, rev_actor, rev_timestamp
) VALUES
(1, 1, 70464, 20100920170330),
(1, 1, 70464, 20101120170330),
(1, 1, 70464, 20100420170330),
(1, 1, 70464, 20100120170330),
(1, 1, 70464, 20101020170330),
(1, 1, 70464, 20101020170330),
-- After edit window
(1, 1, 70464, 20250709170330);
