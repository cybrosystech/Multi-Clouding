##################################
|TITLE| 
##################################

.. |TITLE| replace:: MultiClouding

.. contents:: Table of contents
    :depth: 4

.. sectnum::



************
Introduction
************

This document outlines the implementation of a real-time synchronization mechanism across three servers—Server1, Server2, and Server3. By leveraging inotifywait for monitoring filesystem events and Ansible for executing tasks, this setup ensures that any changes (creation, modification, deletion, or movement of files, git cloning, package installation) in a specified directory on Server1 are promptly and accurately reflected on Server2 and Server3.

*******************
System Architecture
*******************

The architecture consists of:

- Server1: The primary server where file changes are monitored.

- Server2 & Server3: Secondary servers that mirror the specified directory from Server1.

The synchronization process is initiated by inotifywait detecting changes on Server1, which then triggers Ansible playbooks to replicate those changes on Server2 and Server3.

*************
Prerequisites
*************

Before proceeding, ensure the following:

- Operating System: All servers should be running a Unix-like OS (e.g., Ubuntu, CentOS).

- User Access: SSH access with appropriate permissions between Server1 and the other servers.

Installed Tools:

- inotify-tools: For monitoring filesystem events.

- Ansible: For automating tasks across servers.

************************************
Connecting the Servers using Ansible 
************************************

- Server1 - primary server
- Server2 and sever3 - secondary servers

#### Configuration is done using the ssh connection

- Set up the /etc/hosts to connect in 3 servers

```sql
sudo nano /etc/hosts
```

```sql
127.0.0.1       localhost
127.0.1.1       cybrosys
192.168.1.10    server1
192.168.1.11    server2
192.168.1.12    server3
# The following lines are desirable for IPv6 capable hosts
::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
```

- Check the connection from server1

```sql
sudo adduser user
```

- Remove the password 

```sql
sudo passwd -d user
```

- Make the user a sudo user

```sql
sudo usermod -aG sudo user
```

- Install Openssh-server

```sql
sudo apt-get install openssh-server
sudo systemctl start ssh
sudo systemctl enable ssh
```

- Setup ufw

```sql
sudo ufw enable
sudo ufw start
sudo ufw allow 22/tcp
sudo ufw reload
sudo systemctl restart ssh
```

- Install Ansible 

```sql
sudo apt update 
sudo apt install -y ansible git
```

## Server1

- Install Openssh-server


 
