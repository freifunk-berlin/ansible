# backup

Installs and configures restic for our servers.

To use, add the following host_vars:

  - `backup_user`: which user is used on the backup server
  - `backup_password`: which password is used for the backup server AND the backup
  - `backup_directories`: list of directories to backup
  - `backup_role: client`

## Note
The backup server has strict firewall rules **on the virtualization host**. Every client that wants to push backups there needs to be whitelisted.
