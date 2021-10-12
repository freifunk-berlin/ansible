# FF-Berlin Ansible Repo

This repository currently contains our WIP state for the infrastructure code.

It is WIP since we are using it to slowly transition away from Puppet.

The code is, where neccessary, quite debian centric since thats the distribution we use in our infrastructure.




## Requirements
- Ansible 4.x
- The secret encryption password for ansible-vault under `./.vaultpass` 
  - For alternative methods look here: https://docs.ansible.com/ansible/latest/user_guide/vault.html
- access to the hosts
