from pathlib import Path
from platform import freedesktop_os_release
from shutil import which

from dev_share.utils import ShareUtils


class Init(ShareUtils):
    def __init__(self):
        super().__init__()
        self.__install_cmd = self.__set_install_cmd()
        if not self.__install_cmd:
            raise Exception('Unsupported OS or package manager')

    def __set_install_cmd(self) -> str:
        """Set the package manager install command based on the OS

        Returns:
            str: The package manager install command
        """
        os_id = freedesktop_os_release().get('ID_LIKE').lower()
        if 'debian' in os_id:
            return 'sudo apt install -y nfs-common nfs-kernel-server'
        if 'rhel' in os_id:
            if which('dnf'):
                return 'sudo dnf install -y nfs-utils'
            if which('yum'):
                return 'sudo yum install -y nfs-utils'
            self.log.error(f'Unable to find package manager for RHEL based system: {os_id}')
        else:
            self.log.error(f'Unsupported OS: {os_id}')
        return ''

    def __stash_bridge_subnet(self) -> bool:
        """Stash the bridge subnet to a file so it can be referenced later when exporting the NFS share as a default
        parameter

        Returns:
            bool: True if successful, False otherwise
        """
        self.__subnet = self._get_virbr_subnet()
        if self.__subnet:
            try:
                with open(f'{Path(__file__).parent}/share_env/subnet', 'w') as file:
                    file.write(self.__subnet)
                return True
            except Exception:
                self.log.exception('Failed to stash bridge subnet')
        else:
            self.log.error('Failed to get bridge subnet')
        return False

    def __install_system_dependencies(self):
        """Install the system dependencies

        Returns:
            bool: True if successful, False otherwise
        """
        if self.run_cmd(self.__install_cmd)[1]:
            return True
        self.log.error('Failed to install system dependencies')
        return False

    def __determine_firewall_type(self) -> str:
        """Determine the firewall type (ufw or firewalld) and if it is active

        Returns:
            str: The firewall type or an empty string if not found
        """
        for fw in ['ufw', 'firewalld']:
            if which(fw):
                if self.run_cmd(f'sudo systemctl is-active {fw}', True, False)[0].strip() == 'active':
                    return fw
        self.log.info('Could not find firewall type. Skipping firewall configuration. Add manually for your system')
        return ''

    def __set_ufw_server_firewall_config(self) -> bool:
        """Set the server ufw firewall configuration

        Returns:
            bool: True if successful, False otherwise
        """
        for cmd in [f'sudo ufw allow from {self.__subnet} to any port 2049 proto tcp',
                    f'sudo ufw allow from {self.__subnet} to any port 2049 proto udp',
                    'sudo ufw reload']:
            if not self.run_cmd(cmd)[1]:
                self.log.error('Failed to create server ufw firewall rule')
                return False
        return True

    def __set_firewalld_server_firewall_config(self) -> bool:
        """Set the server firewalld firewall configuration

        Returns:
            bool: True if successful, False otherwise
        """
        rich_rule = f'rule family="ipv4" source address="{self.__subnet}" service name="nfs" accept'
        for cmd in [f"sudo firewall-cmd --add-rich-rule='{rich_rule}' --permanent", 'sudo firewall-cmd --reload']:
            if not self.run_cmd(cmd)[1]:
                self.log.error('Failed to create server firewalld firewall rule')
                return False
        return True

    def __set_server_firewall_config(self) -> bool:
        """Determines the firewall type and sets the server firewall configuration if found

        Returns:
            bool: True if successful, False otherwise
        """
        fw = self.__determine_firewall_type()
        if fw == 'ufw':
            return self.__set_ufw_server_firewall_config()
        if fw == 'firewalld':
            return self.__set_firewalld_server_firewall_config()
        return True

    def run_server_init(self) -> bool:
        """Run the server initialization process

        Returns:
            bool: True if successful, False otherwise
        """
        for method in [self.__stash_bridge_subnet, self.__install_system_dependencies,
                       self.__set_server_firewall_config, self._start_and_enable_nfs_server]:
            if not method():
                self.log.debug(f'Failed to initialize server: {method.__name__}')
                return False
        return True

    def run_client_init(self) -> bool:
        """Run the client initialization process

        Returns:
            bool: True if successful, False otherwise
        """
        for method in [self.__install_system_dependencies, self._start_and_enable_nfs_client]:
            if not method():
                self.log.debug(f'Failed to initialize client: {method.__name__}')
                return False
        return True
