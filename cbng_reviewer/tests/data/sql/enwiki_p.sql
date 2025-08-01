-- This is not exactly the same as the labs schema, which is built with views
-- But is compatible enough for test execution

DROP TABLE IF EXISTS page;
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

DROP TABLE IF EXISTS actor;
CREATE TABLE actor (
    actor_id BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
    actor_user INT UNSIGNED DEFAULT NULL,
    actor_name VARBINARY(255) NOT NULL,
    UNIQUE INDEX actor_user (actor_user),
    UNIQUE INDEX actor_name (actor_name),
    PRIMARY KEY(actor_id)
);

DROP TABLE IF EXISTS revision_userindex;
CREATE TABLE revision_userindex (
    rev_id INT UNSIGNED,
    rev_page INT UNSIGNED,
    rev_actor INT UNSIGNED,
    rev_timestamp INT UNSIGNED,
    PRIMARY KEY(rev_actor)
);

DROP TABLE IF EXISTS revision;
CREATE TABLE revision (
    rev_id BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
    rev_page INT UNSIGNED NOT NULL,
    rev_comment_id BIGINT UNSIGNED NOT NULL,
    rev_actor BIGINT UNSIGNED NOT NULL,
    rev_timestamp BINARY(14) NOT NULL,
    rev_minor_edit TINYINT UNSIGNED DEFAULT 0 NOT NULL,
    rev_deleted TINYINT UNSIGNED DEFAULT 0 NOT NULL,
    rev_len INT UNSIGNED DEFAULT NULL,
    rev_parent_id BIGINT UNSIGNED DEFAULT NULL,
    rev_sha1 VARBINARY(32) DEFAULT '' NOT NULL,
    INDEX rev_timestamp (rev_timestamp),
    INDEX rev_page_timestamp (rev_page, rev_timestamp),
    INDEX rev_actor_timestamp (rev_actor, rev_timestamp, rev_id),
    INDEX rev_page_actor_timestamp (
        rev_page, rev_actor, rev_timestamp
    ),
    PRIMARY KEY(rev_id)
);
