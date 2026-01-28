# Tutorials

In this file, you will find some tutorials describing common workflows for using this repository. We generally assume, that all Hosts, that will be managed by this Ansible repository run a recent minimal stable Debian version (at time of writing: Debian 11). Our custom roles do mostly rely on this.

## Prerequisites on to-be-provisioned machine

- VM with Debian11
- Running OpenSSH-Server
- Working SSH-Access to the machine
- minimal python3 installation

## Prerequisites on the provisioning machine

- this repository cloned
- python3 installation
- Ansible installation (`pip install -r requirements.txt`)

We use ansible-vaultpass for storing secrets encrypted in this repository. For provisioning machines with this repository, you need a password in the `.vaultpass` files for decrypting the variables.

## Tutorial for provisioning a new machine

Provisioning a new machine happens in two stages:

1. Set up the users and basic installation
2. Setting it up for its actual purpose

### 1. Set up the basic installation

For this stage, you need to access the machine as root user. Add the machine to the `hosts`-file at `inventory/hosts` and write it into the right section to tag its purpose. For defining a machine to serve as a buildbot worker, it should look like something similar to this:

```ini
[...]

[configserver]
testmachine ansible_host=example.org

```

After that, you can start the first provision stage with `ansible-playbook play.yml --limit=testmachine --tags=user_provision --user root`. As there are no other users yet, you should not forget the `--user root` option.

### 2. Provision machine for its actual purpose

After that, just run the rest of the playbooks for the given machine, accessing it with your own SSH login: `ansible-playbook play.yml --limit=testmachine`. Don't forget to add `--user testuser` if the name of your local user differs from the remote user.

## Provision a machine to buildbotworker

For adding your buildbotworker machine to this repository, we need to follow three steps. The machine does not need to be reachable from the internet. It will connect itself to the buildbot, so it only needs basic access to the internet.

### Get your machine known to Ansible

To get your machine known to Ansible, add it to the `hosts`-file at `inventory/hosts`.

```ini
[buildbotworker]
buildbot-worker-01 ansible_host=85.215.202.123                  # reachable using a public IP
buildbot-worker-02 ansible_host=worker2.example.com             # reachable using a public hostname
buildbot-worker-akira ansible_host=192.168.16.7                 # reachable only from within akiras home using a private IP
buildbot-worker-scherer8 ansible_host=scherer8-buildbot.olsr    # reachable only from within freifunk-net, use a jump-host or so...
```

For the `ansible_host` variable, you can use either hostnames or IP addresses, as stated in the examples above. The host you are going to provision does not need to be reachable from the internet. It is possible to have a host in you local network too. It can get provisioned from your network only then, though.

### Adding variables for buildbot master

Please open `inventory/group_vars/all`. There you will find a list with all workers that are allowed to connect to the buildbot master.

```yml
buildbot_workers:
  - name: example-worker
    passwd: g00d_p455w0rd
    maxbuilds: 1
    cpus_per_build: 4
    notify_on_missing: some_contact
```

Please add your worker underneath:

```yml
buildbot_workers:
  - name: example-worker
    passwd: g00d_p455w0rd
    maxbuilds: 1
    cpus_per_build: 4
    notify_on_missing: some_contact
  - name: MYWORKER
    passwd: g00d_p455w0rd42
    maxbuilds: 1
    cpus_per_build: 2
    notify_on_missing: MY_CONTACT
```

### Adding variables for your worker

In this step, please create a directory for your worker at `inventory/host_vars/MYWORKER`, whereas `MYWORKER` needs to exactly match the workers hostname as you defined it in the `hosts`-file. For this example, it would be `buildbot-worker-MYWORKER`.

In that directory, create a `main.yml`-File, please. You need to define these variables there:

```yml
---
buildbot_worker_name: WORKERNAME
buildbot_worker_pwd: G00D_P455WORD

buildbot_worker_contact: NAME (and contact) of sponsor
buildbot_worker_info: Tell me on your specs. (i.e. VM with 4 Cores, 4GB RAM)
...
```

Please pay attention, that worker name and password match the values, that you've provided to the buildbot master in the `all`-file in the step before.

### Applying config to your worker

As last step, please apply your config with this command:

```sh
ansible-playbook play.yml --limit=buildbot-worker-MYWORKER
```

If your machine is reachable via root only, you may add `--user=root` too.
