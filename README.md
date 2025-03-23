# dev_share

I do a lot of dev work locally on my system utilizing KVM vms. This is a dev tool that I find useful to share files
between my host and guest systems which allows me to dev on my host and test on the guest. It is simply a wrapper around
NFS, but hopefully it will be useful to others and remove some of the manual steps involved in setting up NFS and
sharing files between your dev and qa systems.


# Limitations
The following example uses an `Ubuntu 24.04` host and `rocky 9.5` guest, but it should work on other deb/rpm based
systems.

The user used on the host system should have sudo privileges without a password prompt if possible. The guest user is
expected to use root.

The below expects that KVM is installed on the host system and a virbr0 network is available.


## Server Installation (Host)
The server initialization will try to find the default subnet to allow guest access by parsing the `virbr0` interface.
If it fails, it will prompt for a subnet to use. The subnet is used to create firewall rules and is cached to to be
used as the default subnet in the export config. The initialization will also install the NFS dependencies.


### Create virtual environment
```bash
python3 -m venv venv
```

### Activate virtual environment
```bash
source venv/bin/activate
```

### Install requirements
```bash
pip install -r requirements.txt
```

### Install console scripts
```bash
pip install -e .
```

### Initialize the environment
```bash
# For Server:
dshare --server --init

# Prompt example
Failed to auto-detect virbr subnet. Please enter the subnet manually [192.168.120.0/24]: 192.168.124.0/24

# For Client:
dshare --client --init
```

### Optional: Set command shortcut in your shell RC file (e.g. .bashrc, .zshrc) so you do not have to active venv
```bash
echo "alias shareServer='/<path_to_dir_where_you_created_venv>/venv/bin/python3 dshare' " >> ~/.bashrc
```

# Usage

## Parent Commands:
```bash
dshare -h  
usage: dshare [-h] [-s ...] [-c ...]

Share Commands

options:
  -h, --help            show this help message and exit

  -s ..., --server ...  Share server commands (dshare-server)

  -c ..., --client ...  Share client commands (dshare-client)
```

## Server

### Create Export
The automation will create the export entry in the `/etc/exports` file and reload the exportfs configuration. It will
also start the NFS server service if it is not already running.

```bash
# Create an export directory is not already created
mkdir /exports

# create test file if testing:
echo "this was a test1" >> /exports/test1.txt

# export directory using default subnet and options:
dshare -s -e /exports
# Example output:
Exports:
/exports 192.168.124.0/24(rw,sync,no_subtree_check,no_root_squash)

# Make changes to the options and re-export
dshare -s -e /exports -o rw,sync,no_root_squash
# Example output:
Exports:
/exports 192.168.124.0/24(rw,sync,no_root_squash)

# Add another access IP/subnet to the export
dshare -s -e /exports -a 192.168.123.10
# Example output:
Exports:
/exports 192.168.124.0/24(rw,sync,no_subtree_check,no_root_squash)
/exports 192.168.123.10(rw,sync,no_subtree_check,no_root_squash)

# Allow full access to export (Not Recommended):
dshare -s -e /exports -a '*'
# Example output:
Exports:
/exports *(rw,sync,no_subtree_check,no_root_squash)

# display exports
dshare -s -d
# Example output:
Exports:
/exports 192.168.124.0/24(rw,sync,no_subtree_check,no_root_squash)
/exports 192.168.123.10(rw,sync,no_subtree_check,no_root_squash)
```


### Remove Export
The automation will remove the export entry in the `/etc/exports` file and reload the exportfs configuration.

```bash
# Use --access (-a) to remove specific access IP/subnet
dshare -s --remove /exports -a '*'
# Example output:
Exports:
/exports 192.168.124.0/24(rw,sync,no_subtree_check,no_root_squash)
/exports 192.168.123.10(rw,sync,no_subtree_check,no_root_squash)

# Use --access all to remove all access to an export
dshare -s -R /exports -a all
# Example output:
Exports:
```



## Client

### Create Mount

The automation will automatically create the mount directory if it does not exist. It will also mount the shared
directory to the mount directory and create an fstab entry to ensure the share is mounted on boot.

```bash
dshare --client --create /mnt/test --ip 192.168.124.85 --remote /exports
# Example output:
Successfully mounted 192.168.124.85:/exports --> /mnt/test

# Check the mount 
mount | grep test
192.168.124.85:/exports on /mnt/test type nfs4 (rw,relatime,vers=4.2,rsize=262144,wsize=262144,namlen=255,hard,proto=tcp,timeo=600,retrans=2,sec=sys,clientaddr=192.168.124.242,local_lock=none,addr=192.168.124.85,_netdev)

df -h | grep -i export
192.168.124.85:/exports                     8.9G  3.0G  6.0G  34% /mnt/test

# Check test file we created on the server
cat /mnt/test/test1.txt
this was a test1
```

### Remove Mount
```bash
dshare -c -R /mnt/test
# Example output:
Successfully removed mount /mnt/test
```


# Implementation Details
As mentioned, I use KVM vm for my dev work. To make this tool work effortlessly, I create golden images for OSes that I
need to work on. The golden dev images include the client configuration steps above. That way, all I have to do is
deploy a new VM from the golden image and run the client commands to mount the shared directory.

I work with python often so I create a python virtual environment on the golden image then setup my .bashrc to activate
the venv when I login. That way, I can use the console commands above to add the share storage to the VM. Then I can
navigate to the share directory and run `pip install -e .` which will install the python dev environment that I plan to
work on to the new VM virtual environment.
