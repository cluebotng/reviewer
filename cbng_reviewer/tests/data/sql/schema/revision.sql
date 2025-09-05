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
