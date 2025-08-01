-- Minimal data used in testGetPageCreationMetadata
INSERT INTO page (
    page_id, page_namespace, page_title, page_is_redirect, page_is_new, page_random, page_touched,
    page_links_updated, page_latest, page_len, page_content_model, page_lang
) VALUES (
    29275283, 2, CAST('ClueBot_NG' as binary), 1, 0, 0.777155401146, 20250801095616,
    20250510132841, 1139391397, 39, CAST('wikitext' as binary), NULL
);

INSERT INTO revision (
    rev_id, rev_page, rev_comment_id, rev_actor, rev_timestamp,
    rev_minor_edit, rev_deleted, rev_len, rev_parent_id, rev_sha1
) VALUES (
    391868471, 29275283, 10345, 70464, 20101020170330,
    0, 0, 39, 0, CAST('d2chsbdvb098rhv5e5tczgxq75d7cjm' as binary)
);

INSERT INTO actor (
    actor_id, actor_user, actor_name
) VALUES (
    70464, 2720564, CAST('NaomiAmethyst' as binary)
);