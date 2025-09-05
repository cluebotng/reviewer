CREATE TABLE actor (
    actor_id BIGINT UNSIGNED AUTO_INCREMENT NOT NULL,
    actor_user INT UNSIGNED DEFAULT NULL,
    actor_name VARBINARY(255) NOT NULL,
    UNIQUE INDEX actor_user (actor_user),
    UNIQUE INDEX actor_name (actor_name),
    PRIMARY KEY(actor_id)
);
