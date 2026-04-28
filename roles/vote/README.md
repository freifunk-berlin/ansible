# Deploy your own Loomio

See: https://github.com/loomio/loomio-deploy/blob/master/README.md

## Network configuration

### DNS Records
To allow people to access the site via your hostname you need an A record:

```
A loomio.example.com, 192.0.2.1
```

Loomio supports "Reply by email" and to enable this you need an MX record so mail servers know where to direct these emails.

```
MX loomio.example.com, loomio.example.com, priority 0
```

Additionally, create two CNAME records that point to `loomio.example.com`.

```
CNAME channels.loomio.example.com, loomio.example.com
CNAME hocuspocus.loomio.example.com, loomio.example.com
```

## Configure the server

### SSL teriminating proxy

By default, docker-compose.yml includes an nginx proxy container that automatically handles fetching an SSL certificate via LetsEncrypt.org. If you don't need SSL termination, or you're running Loomio from behind a proxy, you can safely remove the nginx services from the docker-compose.yml file. The loomio app container will happily speak plain HTTP on port 3000 (by default). Configuring reverse proxies and other advanced configurations are outside the scope of this documentation, but at minimum it's suggested to preserve the HTTP host header and to set X-FORWARDED-PROTO if terminating SSL upstream.

### Setup SMTP

You need to bring your own SMTP server for Loomio to send emails.

If you already have an SMTP server, that's great, put the settings into the `env` file.

For everyone else here are some options to consider:

- Look at the (sometimes free) services offered by [SendGrid](https://sendgrid.com/), [SparkPost](https://www.sparkpost.com/), [Mailgun](http://www.mailgun.com/), [Mailjet](https://www.mailjet.com/pricing).

- Setup your own SMTP server with something like Haraka

Edit the `.env` file and enter the right SMTP settings for your setup.

You might also need to add an SPF DNS record to indicate that the SMTP can send mail for your domain.

### Initialize the database
This command initializes a new database for your Loomio instance to use.

```
docker compose up -d db
docker compose run app rake db:setup
```

### Install crontab
Doing this tells the server what regular tasks it needs to run. These tasks include:

* Noticing which proposals are closing in 24 hours and notifying users.
* Closing proposals and notifying users they have closed.
* Sending "Yesterday on Loomio", a digest of activity users have not already read. This is sent to users at 6am in their local timezone.

Run `crontab -e` and append the following line:

```
0 * * * *  /usr/bin/docker exec loomio-worker bundle exec rake loomio:hourly_tasks > ~/rake.log 2>&1
```

## Starting the services
This command starts the database, application, reply-by-email, and live-update services all at once.

```
docker compose up -d
```

Give it a minute to start, then visit your URL while crossing your fingers!

If you visit the url with your browser and the rails server is not yet running, but nginx is, you'll see a "503 bad gateway" error message.

You'll want to see the logs as it all starts, run the following command:

```
docker compose logs -f
```

## Try it out

visit your hostname in your browser.

Once you have signed in (and confirmed your email), grant yourself admin rights

```
docker compose run app rails c
User.last.update(is_admin: true)
```

you can now access the admin interface at https://loomio.example.com/admin


## If something goes wrong

To see system error messages as they happen run `docker compose logs -f` and make a request against the server.

If you want to be notified of system errors you could setup [Sentry](https://sentry.io/) and add it to the env.

Confirm `env` settings are correct.

After you change your `env` files you need to restart the system:

```sh
docker compose down
docker compose up -d
```

To update Loomio to the latest stable version just run the update script.

```sh
./scripts/update
```

To login to your running rails app console:

```sh
docker compose run app rails c
```

A PostgreSQL shell to inspect the database:

```sh
docker exec -ti loomio-db su - postgres -c 'psql loomio_production'
```

## Backups

The default docker-compose.yml includes automatic backups with [prodrigestivill/docker-postgres-backup-local](https://github.com/prodrigestivill/docker-postgres-backup-local), however, you'll need to run `mkdir -p pgdumps && chown -R 999:999 pgdumps` to set the correct permissions for this to work.

You can test that the automatic backup permissions are correct with this command:

```
docker run --rm -v "$PWD:/backups" -u "$(id -u):$(id -g)" --network=loomio-deploy_main -e POSTGRES_HOST=db -e POSTGRES_DB=loomio_production -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=password  prodrigestivill/postgres-backup-local /backup.sh
```

However, sometimes you just want to make or restore an SQL snapshot directly.

Dump SQL
```
docker exec -ti loomio-db su - postgres -c 'pg_dump -c loomio_production' > loomio_production.sql
```

Restore SQL
```
cat loomio_production.sql | docker exec -i loomio-db su - postgres -c 'psql loomio_production'
```
