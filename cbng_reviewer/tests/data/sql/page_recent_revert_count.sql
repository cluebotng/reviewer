-- Minimal data used in testGetPageRecentEditCount
INSERT INTO page (
    page_id, page_namespace, page_title, page_is_redirect, page_is_new, page_random, page_touched,
    page_links_updated, page_latest, page_len, page_content_model, page_lang
) VALUES (
    23253223, 0, CAST('Juicy_Juggles' as binary), 0, 0, 0.777155401146, 20240801095616,
    20240510132841, 1139391397, 39, CAST('wikitext' as binary), NULL
);

INSERT INTO revision (
    rev_id, rev_page, rev_comment_id, rev_actor, rev_timestamp,
    rev_minor_edit, rev_deleted, rev_len, rev_parent_id, rev_sha1
) VALUES
(1, 23253223, 1, 236902581, 20240714170330, 0, 0, 39, 0, ''),
(2, 23253223, 2, 236902578, 20240713170330, 0, 0, 39, 0, ''),
(3, 23253223, 3, 236902576, 20240712170330, 0, 0, 39, 0, ''),
(4, 23253223, 4, 236902561, 20240711170330, 0, 0, 39, 0, ''),
(5, 23253223, 5, 236902580, 20240710170330, 0, 0, 39, 0, ''),
-- Older than edit window:
(6, 23253223, 6, 236902561, 20240611170330, 0, 0, 39, 0, ''),
(7, 23253223, 7, 236902580, 20240510170330, 0, 0, 39, 0, '');

INSERT INTO comment (
    comment_id, comment_hash, comment_text, comment_data
) VALUES
(1, 0, '', ''),
(2, 0, '', ''),
(3, 0, '', ''),
(4, 0, CAST('Revert previous revision' as binary), ''),
(5, 0, '', ''),
(6, 0, '', ''),
(7, 0, CAST('Revert previous revision' as binary), '');
