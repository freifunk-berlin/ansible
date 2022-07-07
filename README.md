# FF-Berlin Ansible Repo

This repository currently contains our WIP state for the infrastructure code.

This is a replacement for the old [puppet repository](https://github.com/freifunk-berlin/puppet).

Keep in mind that we also use ansible to configure the BerlinBackBone, this is done in the [bbb-config repo](https://github.com/freifunk-berlin/bbb-configs).



The code is, where necessary, quite debian centric since that's the distribution we use in our infrastructure.

The Repository also uses a [monorepo](https://en.wikipedia.org/wiki/Monorepo) structure since all the custom roles are only used in this context. 


## Requirements
- Ansible 5.x
- The secret encryption password for ansible-vault under `./.vaultpass` 
  - For alternative methods look here: https://docs.ansible.com/ansible/latest/user_guide/vault.html
- have the necessary requirements installed: `ansible-galay install -r requirements.yml` 
- access to the hosts

## Structure

We follow an adapted version of the [ansible alternative layout](https://docs.ansible.com/ansible/2.8/user_guide/playbooks_best_practices.html#alternative-directory-layout).
Where we put the inventory in an extra directory, but don't use different directories for the stages (Since we don't have any).
Also, the roles are divided into 2 directories, one for external ones, and one for our internal ones.

This separation makes using the monorepo approach easier, since we can just exclude all directories in the `.gitignore`.

```
├── .github                      # Directory for github actions
├── ansible.cfg                  # Custom settings for this Repository
├── external_roles               # Placeholder directory for external roles installed through ansible-galaxy 
├── files                        # Directory for extra files used on the host
├── inventory                    # Directory for our inventory
├── play.yml                     # The single playbook
├── README.md                    # This Readme
├── requirements.yml             # The dependencies to be used with *ansible-galaxy*
├── roles                        # Directory self developed Roles
├── templates                    # Directory for template files
└── Vagrantfile                  # A Vagrant file to run test machines with Vagrant
```

## How to contribute

If you want to help us, you are very welcome.

The easiest way is to ask `@akira` or `@rtznprmpftl` in our [matrix](https://app.element.io/#/room/#berlin.freifunk.net:matrix.org) chatroom.

Alternatively you can use the gitHub bugtracker, if you discover any issues on the infrastructure side.
