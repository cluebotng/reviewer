CREATE TABLE page (
    page_id INT UNSIGNED AUTO_INCREMENT NOT NULL,
    page_namespace INT NOT NULL,
    page_title VARBINARY(255) NOT NULL,
    page_is_redirect TINYINT UNSIGNED DEFAULT 0 NOT NULL,
    page_is_new TINYINT UNSIGNED DEFAULT 0 NOT NULL,
    page_random DOUBLE PRECISION UNSIGNED NOT NULL,
    page_touched BINARY(14) NOT NULL,
    page_links_updated BINARY(14) DEFAULT NULL,
    page_latest INT UNSIGNED NOT NULL,
    page_len INT UNSIGNED NOT NULL,
    page_content_model VARBINARY(32) DEFAULT NULL,
    page_lang VARBINARY(35) DEFAULT NULL,
    UNIQUE INDEX page_name_title (page_namespace, page_title),
        INDEX page_random (page_random),
        INDEX page_len (page_len),
        INDEX page_redirect_namespace_len (
        page_is_redirect, page_namespace,
        page_len
    ),
    PRIMARY KEY(page_id)
);
