# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|

  config.vm.define "buildbot" do |buildbot|
    buildbot.vm.box = "debian/bullseye64"
    buildbot.vm.network "forwarded_port", guest: 80, host: 8080
    buildbot.vm.host_name = "buildbot.berlin.freifunk.net"
  end

  config.vm.define "configserver" do |configserver|
    configserver.vm.box = "debian/buster64"
    configserver.vm.network "forwarded_port", guest: 80, host: 8080
    configserver.vm.host_name = "configserver"


  end

  config.vm.provision "ansible" do |ansible|
      ansible.playbook = "play.yml"
  end

  # disable folder sync since we don't need it
  config.vm.synced_folder ".", "/vagrant", disabled: true
  config.vm.provider :virtualbox do |vb|

    vb.customize ["modifyvm", :id, "--ioapic", "on"]
    vb.memory = 4092
    vb.cpus = 4
  end

end
