from logging import Logger
from subprocess import run
from time import sleep
from pathlib import Path

from dev_share.logger import get_logger
from dev_share.color import Color


class ShareUtils():
    def __init__(self, logger: Logger = None):
        self.log = logger or get_logger('dev-share')

    def _get_virbr_subnet(self, interface: str = 'virbr0') -> str:
        """Get the subnet of the virbr interface. Prompt user if auto-detection fails

        Args:
            interface (str, optional): interface to lookup. Defaults to 'virbr0'.

        Returns:
            str: The subnet of the virbr interface
        """
        rsp = self.run_cmd(f'ip addr show {interface}', True, False)
        if rsp[1]:
            for line in rsp[0].split('\n'):
                if 'inet' in line:
                    return line.split()[1].replace('.1/24', '.0/24')
        else:
            sub = input('Failed to auto-detect virbr subnet. Please enter the subnet manually [192.168.120.0/24]: ')
            if not sub:
                return '192.168.120.0/24'
            return sub
        return ''

    def _get_env_subnet(self) -> str:
        """Get the subnet from the stashed file

        Returns:
            str: The subnet or empty string if not found
        """
        try:
            with open(f'{Path(__file__).parent}/share_env/subnet', 'r') as file:
                return file.read()
        except Exception:
            self.log.exception('Failed to stash bridge subnet')
        return ''

    def run_cmd(self, cmd: str, ignore_error: bool = False, log_output: bool = False) -> tuple:
        """Run a command and return the output

        Args:
            cmd (str): Command to run
            ignore_error (bool, optional): ignore errors. Defaults to False
            log_output (bool, optional): Log command output. Defaults to False.

        Returns:
            tuple: (stdout, True. '') on success or (stdout, False, error) on failure
        """
        state = True
        error = ''
        output = run(cmd, shell=True, capture_output=True, text=True)
        if output.returncode != 0:
            state = False
            error = output.stderr
            if not ignore_error:
                self.log.error(f'Command: {cmd}\nExit Code: {output.returncode}\nError: {error}')
                return '', state, error
        stdout = output.stdout
        if log_output:
            self.log.info(f'Command: {cmd}\nOutput: {stdout}')
        return stdout, state, error

    def is_service_active(self, service: str) -> bool:
        """Check if a service is active

        Args:
            service (str): Service name

        Returns:
            bool: True if active, False otherwise
        """
        return self.run_cmd(f'sudo systemctl is-active {service}', True, False)[0].strip() == 'active'

    def is_service_inactive(self, service: str) -> bool:
        """Check if a service is inactive

        Args:
            service (str): Service name

        Returns:
            bool: True if inactive, False otherwise
        """
        return self.run_cmd(f'sudo systemctl is-active {service}', True, False)[0].strip() == 'inactive'

    def start_service(self, service: str) -> bool:
        """Start a service

        Args:
            service (str): Service name

        Returns:
            bool: True if successful, False otherwise
        """
        if self.run_cmd(f'sudo systemctl start {service}')[1]:
            sleep(1)
            return self.is_service_active(service)
        self.log.error(f'Failed to start service: {service}')
        return False

    def stop_service(self, service: str) -> bool:
        """Stop a service

        Args:
            service (str): Service name

        Returns:
            bool: True if successful, False otherwise
        """
        if self.run_cmd(f'sudo systemctl stop {service}')[1]:
            sleep(1)
            return self.is_service_inactive(service)
        self.log.error(f'Failed to stop service: {service}')
        return False

    @staticmethod
    def display_successful(msg: str) -> None:
        """Display a successful message to console in green

        Args:
            msg (str): Message to display
        """
        Color().print_message(msg, 'green')

    @staticmethod
    def display_failed(msg: str) -> None:
        """Display a failed message to console in red

        Args:
            msg (str): Message to display
        """
        Color().print_message(msg, 'red')


class ShareServer(ShareUtils):
    def __init__(self, logger: Logger = None):
        """Share Server class to manage NFS exports

        Args:
            logger (Logger, optional): logging object to use. Defaults to None.
        """
        super().__init__(logger)
        self.__exports = {}

    @property
    def exports_file(self) -> str:
        """Get the exports file path

        Returns:
            str: Path to the exports file
        """
        return '/etc/exports'

    @property
    def exports(self) -> dict:
        """Get the exports dictionary. If not set, read from file and create exports dict

        Returns:
            dict: Exports dictionary
        """
        if not self.__exports:
            self.__exports = self.__load_exports()
        return self.__exports

    def __load_exports(self) -> dict:
        """Load the exports file into a dictionary

        Returns:
            dict: Exports dictionary
        """
        exports = {}
        try:
            with open(self.exports_file) as file:
                for line in file.readlines():
                    line_split = line.split()
                    right_split = line_split[1].split('(')
                    exports[line_split[0] + right_split[0]] = {'path': line_split[0],
                                                               'client': right_split[0],
                                                               'options': right_split[1].replace(')', '')}
        except Exception:
            self.log.exception('Failed to load exports')
            return {}
        return exports

    def __set_exports_config(self) -> bool:
        """Set the exports file with the exports dictionary data. Display exports to console after setting

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.exports_file, 'w') as file:
                for export in self.exports.values():
                    export: dict
                    file.write(f'{export["path"]} {export["client"]}({export["options"]})\n')
        except Exception:
            self.log.exception('Failed to set exports file')
            return False
        return self.reload_exports() and self.display_exports()

    def __ensure_service_is_running(self) -> bool:
        """Ensure the NFS service is running. If service is not running, attempt to start it

        Returns:
            bool: True if service is running, False otherwise
        """
        if not self.is_service_active('nfs-server'):
            self.log.debug('Starting NFS service')
            return self.start_service('nfs-server')
        return True

    def reload_exports(self) -> bool:
        """Reload the exports file data

        Returns:
            bool: True if successful, False otherwise
        """
        if self.run_cmd('sudo exportfs -rav')[1]:
            return self.__ensure_service_is_running()
        self.log.error('Failed to reload exports')
        return False

    def add_export(self, export_path: str, client: str,
                   options: str = 'rw,sync,no_subtree_check,no_root_squash') -> bool:
        """Add an export to the exports file so clients can import and mount the share

        Args:
            export_path (str): the path to export
            client (str): the client IP or subnet to allow access
            options (str, optional): export options. Defaults to 'rw,sync,no_subtree_check,no_root_squash'.

        Returns:
            bool: True if successful, False otherwise
        """
        if not Path(export_path).exists():
            self.log.error(f'Export path does not exist {export_path}')
            return False
        for export_name in self.exports:
            if export_name == export_path + client:
                self.exports[export_name] = {'path': export_path, 'client': client, 'options': options}
                return self.__set_exports_config()
        self.exports[export_path + client] = {'path': export_path, 'client': client, 'options': options}
        return self.__set_exports_config()

    def remove_export(self, export_path: str, client: str = 'all') -> bool:
        """Remove an export from the exports file. If client is 'all', remove all exports with the export path, else
        just remove the export with the client IP/subnet

        Args:
            export_path (str): the path to export
            client (str, optional): the client/IP/subnet. Defaults to 'all'.

        Returns:
            bool: True if successful, False otherwise
        """
        if client == 'all':
            export_names = list(self.exports.keys())
            for export_name in export_names:
                if export_name.startswith(export_path):
                    self.exports.pop(export_name)
        else:
            export_name = export_path + client
            if export_name in self.exports:
                self.exports.pop(export_name)
            else:
                self.log.info('Export not found')
                return True
        return self.__set_exports_config()

    def display_exports(self) -> bool:
        """Display the exports file data to console

        Returns:
            bool: True if successful, False otherwise
        """
        data = 'Exports:\n'
        try:
            with open('/etc/exports', 'r') as file:
                data += file.read()
        except Exception:
            self.log.exception('Failed to read exports file')
            return False
        self.display_successful(data.strip())
        return True


class ShareClient(ShareUtils):
    def __init__(self, logger: Logger = None):
        """Share Client class to manage NFS mounts

        Args:
            logger (Logger, optional): logging object to use. Defaults to None.
        """
        super().__init__(logger)

    def mount_all(self) -> bool:
        """Mount all shares in the fstab file

        Returns:
            bool: True if successful, False otherwise
        """
        if self.run_cmd('mount -a')[1]:
            return True
        self.log.error('Failed to mount all fstab shares')
        return False

    def __create_fstab_entry(self, entry: str) -> bool:
        """Create an entry in the fstab file. If the entry already exists (based on remote IP and export), return True.
        This will not update the entry if the options are different. Remove the entry first if you want to update it

        Args:
            entry (str): Entry to add to the fstab file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open('/etc/fstab', 'r') as file:
                if entry.split()[0] in file.read():
                    self.log.debug('Entry already exists in fstab')
                    return True
            with open('/etc/fstab', 'a') as file:
                file.write(f'{entry}\n')
            self.log.debug('Successfully created fstab entry')
            return True
        except Exception:
            self.log.exception('Failed to create fstab entry')
        return False

    def __remove_fstab_entry(self, mount: str) -> bool:
        """Remove an entry from the fstab file

        Args:
            mount (str): Mount path to remove

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            payload = []
            with open('/etc/fstab', 'r') as file:
                for line in file.readlines():
                    if mount in line:
                        continue
                    payload.append(line)
            with open('/etc/fstab', 'w') as file:
                file.write(''.join(payload))
            return True
        except Exception:
            self.log.exception(f'Failed to remove fstab entry for mount {mount}')
        return False

    def create_mount(self, server_ip: str, share_path: str, mount: str,
                     options: str = 'defaults,nofail,_netdev') -> bool:
        """Create a mount point and add it to the fstab file

        Args:
            server_ip (str): remote NFS server IP
            share_path (str): remote NFS share path
            mount (str): local mount path
            options (str, optional): mount options to add to fstab entry. Defaults to 'defaults,nofail,_netdev'.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            Path(mount).mkdir(parents=True, exist_ok=True)
        except Exception:
            self.log.exception(f'Failed to create mount directory: {mount}')
            return False
        if self.__create_fstab_entry(f'{server_ip}:{share_path} {mount} nfs {options} 0 0'):
            if self.mount_all():
                self.display_successful(f'Successfully mounted {server_ip}:{share_path} --> {mount}')
                return True
        self.log.error('Failed to create mount')
        return False

    def remove_mount(self, mount: str) -> bool:
        """Remove a mount point and entry from the fstab file

        Args:
            mount (str): Mount path to remove

        Returns:
            bool: True if successful, False otherwise
        """
        if not Path(mount).is_mount():
            self.log.error(f'Mount path does not exist: {mount}')
            return False
        if self.run_cmd(f'umount {mount}')[1] and self.__remove_fstab_entry(mount):
            self.display_successful(f'Successfully removed mount {mount}')
            return True
        self.log.error(f'Failed to remove {mount}')
        return False
