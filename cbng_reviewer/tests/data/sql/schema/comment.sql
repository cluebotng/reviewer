CREATE TABLE comment (
    comment_id BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
    comment_hash INT NOT NULL,
    comment_text BLOB NOT NULL,
    comment_data BLOB DEFAULT NULL,
    INDEX comment_hash (comment_hash),
    PRIMARY KEY(comment_id)
);
