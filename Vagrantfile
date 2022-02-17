# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|

  config.vm.define "buildbot" do |buildbot|
    buildbot.vm.box = "debian/bullseye64"
    buildbot.vm.network "forwarded_port", guest: 80, host: 8080
    buildbot.vm.host_name = "buildbot.berlin.freifunk.net"

    config.vm.provision "ansible" do |ansible|
        ansible.playbook = "play.yml"
    end
  end


  config.vm.provider :virtualbox do |vb|
    vb.memory = 2048
    vb.cpus = 2
  end

end
