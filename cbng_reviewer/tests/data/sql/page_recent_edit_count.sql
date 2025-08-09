-- Minimal data used in testGetPageRecentEditCount
INSERT INTO page (
    page_id, page_namespace, page_title, page_is_redirect, page_is_new, page_random, page_touched,
    page_links_updated, page_latest, page_len, page_content_model, page_lang
) VALUES (
    29273823, 0, CAST('Bimble_Bottle' as binary), 0, 0, 0.777155401146, 20250801095616,
    20250510132841, 1139391397, 39, CAST('wikitext' as binary), NULL
);

INSERT INTO revision (
    rev_id, rev_page, rev_comment_id, rev_actor, rev_timestamp,
    rev_minor_edit, rev_deleted, rev_len, rev_parent_id, rev_sha1
) VALUES
(1, 29273823, 10345, 236902581, 20250714170330, 0, 0, 39, 0, ''),
(2, 29273823, 10345, 236902578, 20250713170330, 0, 0, 39, 0, ''),
(3, 29273823, 10345, 236902576, 20250712170330, 0, 0, 39, 0, ''),
(4, 29273823, 10345, 236902561, 20250711170330, 0, 0, 39, 0, ''),
(5, 29273823, 10345, 236902580, 20250710170330, 0, 0, 39, 0, ''),
-- Older than edit window:
(6, 29273823, 10345, 236902561, 20250611170330, 0, 0, 39, 0, ''),
(7, 29273823, 10345, 236902580, 20250510170330, 0, 0, 39, 0, '');
