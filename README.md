ClueBot NG - Review Interface
=============================

The review interface handles (trusted) human review of filtered reports & false positive/negative/random edits.

It is designed to be the main source of data for training the [https://github.com/cluebotng/core](core) ANN.

# Runtime dependencies

## MySQL/MariaDB

Required for storing review data.

Configuration via environment variables:

* `TOOL_TOOLSDB_HOST` - database host. default: `localhost`
* `TOOL_TOOLSDB_USER` - database user. default: `root`
* `TOOL_TOOLSDB_PASSWORD` - database password. default: ``

## Secrets

Required for Django:

* `DJANGO_SECRET_KEY`

Required for (OAuth) authentication:

* `OAUTH_TOKEN`
* `OAUTH_SECRET`

# Deployment

The production deployment is handled via a build pack,
see https://wikitech.wikimedia.org/wiki/Help:Toolforge/Building_container_images for more details.

## Development

For development purposes a local configuration file will be required along the lines of

```
django:
  debug: true

# Local redirect url
oauth:
  key: xxxx
  secret: xxxx

mysql:
  # Port forwarded
  replica:
    host: 127.0.0.1
    port: 3316
```

## Production

### Setup

A number of environment variables needs to be created prior to the first deployment:

* DJANGO_SECRET_KEY
* OAUTH_KEY
* OAUTH_SECRET
* WIKIPEDIA_USERNAME
* WIKIPEDIA_PASSWORD
* TOOL_TOOLSDB_SCHEMA
* PYTHONUNBUFFERED

### Maintenance

To prevent new reviews from being added while updating the system, `admin_mode` can be enabled

```
toolforge envvar create CBNG_ADMIN_ONLY true
```

Removing the env var or setting to a value other than `true` will disable `admin_mode`.

### Deployment

Ideally everything would be deployed on push, however web services are not currently supported.

For now, things can be managed using `fabric` as with the production bot.

```
fab deploy
```

When webservices are supported, migrating `jobs.yaml` to a component config should be reasonably straight forward.
