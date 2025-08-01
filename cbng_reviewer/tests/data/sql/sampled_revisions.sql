-- Minimal data used in testSampledEdits
INSERT INTO page (
    page_id, page_namespace, page_title, page_is_redirect, page_is_new, page_random, page_touched,
    page_links_updated, page_latest, page_len, page_content_model, page_lang
) VALUES (
    57160200, 0, CAST('People_executed_during_the_Iranian_Revolution' as binary), 0, 0, 0.7, DATE_FORMAT(NOW(), "%Y%m%d%H%i%S"),
    DATE_FORMAT(NOW(), "%Y%m%d%H%i%S"), 1288311442, 252, CAST('wikitext' as binary), NULL
);

INSERT INTO revision (
    rev_id, rev_page, rev_comment_id, rev_actor, rev_timestamp,
    rev_minor_edit, rev_deleted, rev_len, rev_parent_id, rev_sha1
) VALUES (
    1266506804, 57160200, 470082501, 3351, DATE_FORMAT((NOW() - INTERVAL 1 DAY), "%Y%m%d%H%i%S"),
    1, 0, 211, 1250742711, CAST("4v2vctrh55r356n6zxi2pt5poyvunoz" as binary)
);
