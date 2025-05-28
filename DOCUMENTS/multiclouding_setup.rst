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

**********************************************
Configuration is done using the ssh connection
**********************************************

- Set up the /etc/hosts to connect in 3 servers

.. code-block:: console

   $ sudo nano /etc/hosts

.. code-block:: bash

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

- Check the connection from server1

.. code-block:: console

   $ sudo adduser user

- Remove the password 

.. code-block:: console

   $ sudo passwd -d user

- Make the user a sudo user

.. code-block:: console

   $ sudo usermod -aG sudo user

- Install Openssh-server

.. code-block:: console

   $ sudo apt-get install openssh-server
   $ sudo systemctl start ssh
   $ sudo systemctl enable ssh

- Setup ufw

.. code-block:: console

   $ sudo ufw enable
   $ sudo ufw start
   $ sudo ufw allow 22/tcp
   $ sudo ufw reload
   $ sudo systemctl restart ssh

- Install Ansible 

.. code-block:: console

   $ sudo apt update 

*******
Server1
*******

- Install Openssh-server

.. code-block:: console

   $ sudo apt-get install openssh-server
   $ sudo systemctl start ssh
   $ sudo systemctl enable ssh
 
- Setup ufw

.. code-block:: console

   $ sudo ufw enable
   $ sudo ufw start
   $ sudo ufw allow 22/tcp
   $ sudo ufw reload
   $ sudo systemctl restart ssh

- Install Ansible

.. code-block:: console

   $ sudo apt-get update
   $ sudo apt-get install -y ansible

- Create new directory inventories

.. code-block:: console

   $ mkdir -p /home/cybrosys/inventories

- Create the ansible hosts file

.. code-block:: console

   $ sudo nano /home/cybrosys/inventories/hosts

- Add the following

.. code-block:: bash

   [lab]
   server2 ansible_host=192.168.1.11 ansible_user=user
   server3 ansible_host=192.168.1.12 ansible_user=user

- Check the connection with server2 and server3 using ssh

.. code-block:: console

   $ ssh user@server2
   $ exit
   $ ssh user@server3
   $ exit

- If the public key error occurs in case of ssh 
Set the password authentication as no in /etc/ssh/ssh_config file in server1

.. code-block:: bash

   passwordAuthentication no

Generate ssh key

.. code-block:: console

   $ ssh-keygen -t rsa -b 4096

Get the public key

.. code-block:: console

   $ cat ~/.ssh/id_rsa.pub

Manually add the key in server2 and server3

.. code-block:: console

   $ sudo -i -u user
   $ mkdir -p ~/.ssh
   $ chmod 700 ~/.ssh
   $ echo "<PASTE_THE_KEY_HERE>"
   $ chmod 600 ~/.ssh/authorized_keys
   $ chown -R user:user ~/.ssh
   $ sudo systemctl restart ssh
   $ ssh user@server2

- Check the connection

.. code-block:: console

   $ ansible all -m ping -i inventories/hosts

- Install python simple json in secondary servers using ansible

.. code-block:: console

   $ ansible lab -i inventories/hosts -m raw -a 'sudo apt-get -y install python3-simplejson' -become

- Install inotify tools

.. code-block:: console

   $ sudo apt update
   $ sudo apt install -y ansible inotify-tools git

- To monitor package installations on Server1

.. code-block:: console

   $ sudo nano /usr/local/bin/package-sync.sh

- To make the script executable 

.. code-block:: console

   $ sudo chmod +x /usr/local/bin/package-sync.sh

- Runs package-sync.sh in the background, so it keeps monitoring without stopping after logout.

.. code-block:: console

   $ sudo nohup /usr/local/bin/package-sync.sh > /dev/null 2>&1 &

- To set the cron job

.. code-block:: console

   $ crontab -e

Add the following

.. code-block:: bash

   @reboot nohup /home/cybrosys/watch_packages.sh
   */5 * * * * /bin/bash /home/cybrosys/watch_packages.sh >> /tmp/watch_packages.log 2>&1

- To automatically monitor package installations and removals on primary server and synchronize them across secondary servers using Ansible, 
  To automatically monitor then create and remove directories and files
  To automatically clone git 
  To automatically update and upgrade 
  To automatically monitor the service file status
  To automatically sync the files and directories

.. code-block:: console

   $ sudo nano /home/cybrosys/watch_packages.sh

Add this

.. code-block:: bash

   #!/bin/bash
   source ~/.bashrc
   LOGFILE="/var/log/watch_packages.log"
   PKG_LIST="/tmp/packages_list.txt"
   CRITICAL_PKGS="libc6 libstdc++6 ubuntu-minimal ubuntu-standard"
   GIT_DIR="$HOME"
   SYNC_DIR="${1:-$HOME}"
   ANSIBLE_GROUP="lab"
   INVENTORY="inventories/hosts"
   PG_USER="postgres"
   PG_PASS="cool"

   echo "$(date) - Starting server synchronization..." | tee -a "$LOGFILE"

   monitor_packages() {
       while true; do
           sleep 20
           NEW_PKG_LIST="/tmp/packages_list_new.txt"
           dpkg-query -W -f='${Package}\n' | sort > "$NEW_PKG_LIST"
        
           if [ ! -f "$PKG_LIST" ]; then
               cp "$NEW_PKG_LIST" "$PKG_LIST"
               continue
           fi

           ansible $ANSIBLE_GROUP -m ping -i $INVENTORY > /dev/null 2>&1
           if [ $? -ne 0 ]; then
               echo "$(date) - ERROR: Secondary servers unreachable. Skipping package sync." | tee -a "$LOGFILE"
               continue
           fi

           for pkg in $(comm -13 "$PKG_LIST" "$NEW_PKG_LIST"); do
               echo "$(date) - Installing $pkg on secondary servers..." | tee -a "$LOGFILE"
               ansible $ANSIBLE_GROUP -m apt -a "name=$pkg state=latest update_cache=yes" --become -i $INVENTORY | tee -a "$LOGFILE"
           done

           for pkg in $(comm -23 "$PKG_LIST" "$NEW_PKG_LIST"); do
               if echo "$CRITICAL_PKGS" | grep -qw "$pkg"; then
                   echo "$(date) - Reinstalling critical package $pkg..." | tee -a "$LOGFILE"
                   ansible $ANSIBLE_GROUP -m apt -a "name=$pkg state=latest" --become -i $INVENTORY
               else
                   PKG_FOUND=$(ansible $ANSIBLE_GROUP -m shell -a "dpkg -l | grep -w $pkg" --become -i $INVENTORY | grep -c "$pkg")
                   if [ "$PKG_FOUND" -gt 0 ]; then
                       echo "$(date) - Removing $pkg from secondary servers..." | tee -a "$LOGFILE"
                       ansible $ANSIBLE_GROUP -m apt -a "name=$pkg state=absent autoremove=yes purge=yes" --become -i $INVENTORY
                   else
                       echo "$(date) - Package $pkg not found on secondary servers, skipping removal." | tee -a "$LOGFILE"
                   fi
               fi
           done

           mv "$NEW_PKG_LIST" "$PKG_LIST"
       done
   }

   monitor_services() {
       SERVICES=("nginx" "apache2")
       declare -A LAST_STATUS

       while true; do
           sleep 60
           ansible $ANSIBLE_GROUP -m ping -i $INVENTORY > /dev/null 2>&1
           if [ $? -ne 0 ]; then
               echo "$(date) - ERROR: Secondary servers unreachable. Skipping service sync." | tee -a "$LOGFILE"
               continue
           fi

           for SERVICE_NAME in "${SERVICES[@]}"; do
               CURRENT_STATUS=$(systemctl is-active "$SERVICE_NAME")
               if [[ "$CURRENT_STATUS" == "active" && "${LAST_STATUS[$SERVICE_NAME]}" != "active" ]]; then
                   echo "$(date) - Starting $SERVICE_NAME on secondary servers..." | tee -a "$LOGFILE"
                   ansible $ANSIBLE_GROUP -m systemd -a "name=$SERVICE_NAME state=started" --become -i $INVENTORY
               elif [[ "$CURRENT_STATUS" == "inactive" && "${LAST_STATUS[$SERVICE_NAME]}" != "inactive" ]]; then
                   echo "$(date) - Stopping $SERVICE_NAME on secondary servers..." | tee -a "$LOGFILE"
                   ansible $ANSIBLE_GROUP -m systemd -a "name=$SERVICE_NAME state=stopped" --become -i $INVENTORY
               fi
               LAST_STATUS[$SERVICE_NAME]=$CURRENT_STATUS
           done
       done
   }

   update_and_upgrade() {
       while true; do
           sleep 50
           ansible $ANSIBLE_GROUP -m ping -i $INVENTORY > /dev/null 2>&1
           if [ $? -ne 0 ]; then
               echo "$(date) - ERROR: Secondary servers unreachable. Skipping update & upgrade." | tee -a "$LOGFILE"
               continue
           fi
           echo "$(date) - Running update & upgrade on all servers..." | tee -a "$LOGFILE"
           ansible $ANSIBLE_GROUP -m apt -a "update_cache=yes upgrade=yes" --become -i $INVENTORY
       done
   }

   monitor_git() {
       while true; do
           sleep 20
           echo "$(date) - Starting Git synchronization..." | tee -a "$LOGFILE"
           ansible $ANSIBLE_GROUP -m ping -i $INVENTORY > /dev/null 2>&1
           if [ $? -ne 0 ]; then
               echo "$(date) - ERROR: Secondary servers unreachable. Skipping Git sync." | tee -a "$LOGFILE"
               continue
           fi
           ansible $ANSIBLE_GROUP -m file -a "path=$GIT_DIR state=directory mode=0755" --become -i $INVENTORY
           ansible $ANSIBLE_GROUP -m apt -a "name=git state=present update_cache=yes" --become -i $INVENTORY

           if [ ! "$(ls -A $GIT_DIR 2>/dev/null)" ]; then
               echo "$(date) - WARNING: No repositories found in $GIT_DIR" | tee -a "$LOGFILE"
           fi

           for repo in "$GIT_DIR"/*; do
               if [ -d "$repo/.git" ]; then
                   REPO_NAME=$(basename "$repo")
                   REPO_URL=$(git -C "$repo" remote get-url origin)
                   echo "$(date) - Checking repo: $repo, URL: $REPO_URL" | tee -a "$LOGFILE"
                   EXISTS=$(ansible $ANSIBLE_GROUP -m shell -a "test -d $GIT_DIR/$REPO_NAME && echo exists" --become -i $INVENTORY | grep -c "exists")
                   if [ "$EXISTS" -eq 0 ]; then
                       echo "$(date) - Cloning $REPO_NAME on secondary servers..." | tee -a "$LOGFILE"
                       ansible $ANSIBLE_GROUP -m shell -a "git clone $REPO_URL $GIT_DIR/$REPO_NAME" --become -i $INVENTORY 2>&1 | tee -a "$LOGFILE"
                   else
                       echo "$(date) - Pulling latest changes for $REPO_NAME on secondary servers..." | tee -a "$LOGFILE"
                       ansible $ANSIBLE_GROUP -m shell -a "git -C $GIT_DIR/$REPO_NAME pull" --become -i $INVENTORY 2>&1 | tee -a "$LOGFILE"
                   fi
               fi
           done
       done
   }

   monitor_directory_and_files() {
       echo "$(date) - Monitoring directory for real-time changes..." | tee -a "$LOGFILE"
       inotifywait -m -r -e create,modify,move "$SYNC_DIR" --format '%e %w%f' |
       while read -r EVENT FILE_PATH; do
           RELATIVE_PATH="${FILE_PATH#$SYNC_DIR/}"
           case "$EVENT" in
               *CREATE*)
                   if [ -d "$FILE_PATH" ]; then
                       echo "$(date) - Creating directory $RELATIVE_PATH on secondary servers..." | tee -a "$LOGFILE"
                       ansible "$ANSIBLE_GROUP" -m file -a "path=$SYNC_DIR/$RELATIVE_PATH state=directory mode=0755" --become -i "$INVENTORY"
                   else
                       echo "$(date) - Creating file $RELATIVE_PATH on secondary servers..." | tee -a "$LOGFILE"
                       ansible "$ANSIBLE_GROUP" -m copy -a "src=$FILE_PATH dest=$SYNC_DIR/$RELATIVE_PATH" --become -i "$INVENTORY"
                   fi
                   ;;
               *MODIFY*)
                   if [ ! -d "$FILE_PATH" ]; then
                       echo "$(date) - Updating file $RELATIVE_PATH on secondary servers..." | tee -a "$LOGFILE"
                       ansible "$ANSIBLE_GROUP" -m copy -a "src=$FILE_PATH dest=$SYNC_DIR/$RELATIVE_PATH" --become -i "$INVENTORY"
                   fi
                   ;;
               *MOVE*)
                   echo "$(date) - Moving or renaming $RELATIVE_PATH on secondary servers..." | tee -a "$LOGFILE"
                   ansible "$ANSIBLE_GROUP" -m synchronize -a "src=$SYNC_DIR/ dest=$SYNC_DIR/ recursive=yes" --become -i "$INVENTORY"
                   ;;
               *)
                   echo "$(date) - Unhandled event: $EVENT for $FILE_PATH" | tee -a "$LOGFILE"
                   ;;
           esac
       done
   }

   sync_permissions() {
       SCRIPT_PATH="$(realpath "$0")"
       echo "$(date) - Ensuring script $SCRIPT_PATH has executable permission on all secondary servers..." | tee -a "$LOGFILE"
       ansible "$ANSIBLE_GROUP" -m file -a "path=$SCRIPT_PATH mode=0755" --become -i "$INVENTORY"
       if [ $? -eq 0 ]; then
           echo "$(date) - Script permissions updated successfully on all secondary servers." | tee -a "$LOGFILE"
       else
           echo "$(date) - ERROR: Failed to update script permissions on secondary servers." | tee -a "$LOGFILE"
       fi
   }

   # Start monitoring processes
   #sync_directories_and_files & 
   monitor_directory_and_files &
   monitor_packages &
   monitor_services &
   update_and_upgrade &
   monitor_git &
   sync_permissions &

   # Wait for background processes
   wait

   /;.

- To grant execution permissions to the watch_packages.sh

.. code-block:: console

   $ sudo chmod +x ~/watch_packages.sh

- Restart the script

.. code-block:: console

   $ nohup ~/watch_packages.sh &

- To create an empty log file

.. code-block:: console

   $ sudo touch /var/log/watch_packages.log 

- To allow the script to write logs

.. code-block:: console

   $ sudo chmod 666 /var/log/watch_packages.log

- To execute script with superuser privileges

.. code-block:: console

   $ sudo nohup /home/cybrosys/watch_packages.sh &

- To test the working of the automation file

Install the htop in server1

.. code-block:: console

   $ sudo apt install -y htop

Check the installation of htop in server1

.. code-block:: console

   $ dpkg -l | grep htop

Check the installation of htop in server2 from server1

.. code-block:: console

   $ ansible lab -m shell -a "dpkg -l | grep -i htop" -i inventories/hosts

**********************
Install & Setup Odoo18
**********************

- Create a shell script to install and setup odoo18 

.. code-block:: console

   $ sudo nano install_odoo18.sh

Add the following

.. code-block:: bash

   #!/bin/bash

   # Exit on any error
   set -e

   echo "=== Updating system packages ==="
   sudo apt update
   sudo apt upgrade -y

   echo "=== Securing the server ==="
   sudo apt install -y openssh-server fail2ban
   sudo systemctl start fail2ban
   sudo systemctl enable fail2ban
   sudo systemctl status fail2ban

   echo "=== Installing required packages and libraries ==="
   sudo apt install -y python3-pip python3-dev libxml2-dev libxslt1-dev zlib1g-dev \
   libsasl2-dev libldap2-dev build-essential libssl-dev libffi-dev libmysqlclient-dev \
   libjpeg-dev libjpeg8-dev liblcms2-dev libblas-dev libatlas-base-dev \
   libpq-dev npm node-less git python3-venv xfonts-75dpi

   echo "=== Creating symlink for Node.js (if needed) ==="
   if [ ! -f /usr/bin/node ]; then
     sudo ln -s /usr/bin/nodejs /usr/bin/node
   fi

   echo "=== Installing Less and Clean CSS ==="
   sudo npm install -g less less-plugin-clean-css

   echo "=== Installing PostgreSQL and creating Odoo DB user ==="
   sudo apt install -y postgresql
   sudo -u postgres createuser --createdb --username postgres --no-createrole --superuser --pwprompt odoo

   echo "=== Creating system user for Odoo ==="
   sudo adduser --system --home=/opt/odoo --group odoo

   echo "=== Cloning Odoo 18 Community Edition ==="
   sudo su - odoo -s /bin/bash -c "git clone https://github.com/odoo/odoo.git --depth 1 --branch 18.0 --single-branch /opt/odoo"

   echo "=== Setting up Python virtual environment ==="
   sudo python3 -m venv /opt/odoo/venv310
   source /opt/odoo/venv310/bin/activate
   pip install -r /opt/odoo/requirements.txt
   deactivate

   echo "=== Installing wkhtmltopdf and OpenSSL dependencies ==="
   cd /tmp
   wget https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.5/wkhtmltox_0.12.5-1.bionic_amd64.deb
   wget http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.1f-1ubuntu2_amd64.deb
   sudo dpkg -i libssl1.1_1.1.1f-1ubuntu2_amd64.deb || true
   sudo dpkg -i wkhtmltox_0.12.5-1.bionic_amd64.deb || true
   sudo apt install -f -y

   echo "=== Creating log directory ==="
   sudo mkdir -p /var/log/odoo
   sudo chown odoo:root /var/log/odoo

   echo "=== Creating Odoo configuration file ==="
   sudo bash -c 'cat > /etc/odoo.conf <<EOF
   [options]
   admin_passwd = cool
   db_host = False
   db_port = False
   db_user = odoo
   db_password = cool
   addons_path = /opt/odoo/addons, /opt/odoo/custom_addons
   default_productivity_apps = True
   logfile = /var/log/odoo/odoo.log
   EOF'
   sudo chmod 640 /etc/odoo.conf
   sudo chown odoo: /etc/odoo.conf

   echo "=== Creating systemd service ==="
   sudo bash -c 'cat > /etc/systemd/system/odoo.service <<EOF
   [Unit]
   Description=Odoo 18
   Documentation=http://www.odoo.com
   [Service]
   Type=simple
   User=odoo
   ExecStart=/opt/odoo/venv310/bin/python3 /opt/odoo/odoo-bin -c /etc/odoo.conf
   [Install]
   WantedBy=multi-user.target
   EOF'

   echo "=== Reloading systemd and starting Odoo ==="
   sudo systemctl daemon-reload
   sudo systemctl enable odoo
   sudo systemctl start odoo
   sudo systemctl status odoo
