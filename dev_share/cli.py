from argparse import REMAINDER

from dev_share.arg_parser import ArgParser


def parse_parent_args(args: dict):
    if args.get('server'):
        return share_server(args['server'])
    if args.get('client'):
        return share_client(args['client'])
    return True


def share_parent():
    args = ArgParser('Share Commands', None, {
        'server': {
            'short': 's',
            'help': 'Share server commands (dshare-server)',
            'nargs': REMAINDER
        },
        'client': {
            'short': 'c',
            'help': 'Share client commands (dshare-client)',
            'nargs': REMAINDER
        },
    }).set_arguments()
    if not parse_parent_args(args):
        exit(1)
    exit(0)


def parse_server_args(args: dict):
    from dev_share.utils import ShareServer
    if args.get('start'):
        return ShareServer().start_service('nfs-server')
    if args.get('status'):
        return ShareServer().service_status('nfs-server')
    if args.get('stop'):
        return ShareServer().stop_service('nfs-server')
    if args.get('reload'):
        return ShareServer().reload_exports()
    if args.get('export'):
        return ShareServer().add_export(args['export'], args['access'], args['options'])
    if args.get('remove'):
        return ShareServer().remove_export(args['remove'], args['access'])
    if args.get('display'):
        return ShareServer().display_exports()
    if args.get('init'):
        from dev_share.init import Init
        return Init().run_server_init()
    return True


def share_server(parent_args: list = None):
    from dev_share.utils import ShareUtils
    subnet = ShareUtils()._get_env_subnet() or '*'
    args = ArgParser('Share Server', parent_args, {
        'access': {
            'short': 'a',
            'help': f'access IP or subnet for export. Default: {subnet}',
            'default': subnet,
        },
        'display': {
            'short': 'd',
            'help': 'display exports',
            'action': 'store_true',
        },
        'export': {
            'short': 'e',
            'help': 'export directory (Provide full path)',
        },
        'init': {
            'short': 'I',
            'help': 'initialize server service',
            'action': 'store_true'
        },
        'options': {
            'short': 'o',
            'help': 'export options. Default: rw,sync,no_subtree_check,no_root_squash',
            'default': 'rw,sync,no_subtree_check,no_root_squash',
        },
        'reload': {
            'short': 'r',
            'help': 'reload export configuration',
            'action': 'store_true'
        },
        'remove': {
            'short': 'R',
            'help': 'remove export directory (Provide full path)',
        },
        'start': {
            'short': 's',
            'help': 'start server service',
            'action': 'store_true',
        },
        'status': {
            'short': 'st',
            'help': 'server service status',
            'action': 'store_true',
        },
        'stop': {
            'short': 'S',
            'help': 'stop server service',
            'action': 'store_true'
        },
    }).set_arguments()
    if not parse_server_args(args):
        exit(1)
    exit(0)


def parse_client_args(args: dict):
    from dev_share.utils import ShareClient
    if args.get('start'):
        return ShareClient().start_service('nfs-client.target')
    if args.get('status'):
        return ShareClient().service_status('nfs-client.target')
    if args.get('stop'):
        return ShareClient().stop_service('nfs-client.target')
    if args.get('create'):
        if not args.get('ip') or not args.get('remote'):
            print('IP and remote directory are required when creating a mount point')
            return False
        return ShareClient().create_mount(args['ip'], args['remote'], args['create'], args['options'])
    if args.get('remove'):
        return ShareClient().remove_mount(args['remove'])
    if args.get('init'):
        from dev_share.init import Init
        return Init().run_client_init()
    return True


def share_client(parent_args: list = None):
    args = ArgParser('Share Client', parent_args, {
        'create': {
            'short': 'c',
            'help': 'create mount point (Provide full path to new mount point)',
        },
        'init': {
            'short': 'I',
            'help': 'initialize client service',
            'action': 'store_true'
        },
        'ip': {
            'short': 'i',
            'help': 'server IP address to use when creating mount point',
        },
        'options': {
            'short': 'o',
            'help': 'mount options. Default: defaults,nofail,_netdev',
            'default': 'defaults,nofail,_netdev',
        },
        'remote': {
            'short': 'r',
            'help': 'remote directory to mount when creating mount point',
        },
        'remove': {
            'short': 'R',
            'help': 'remove mount point (Provide full path to mount point)',
        },
        'start': {
            'short': 's',
            'help': 'start client service',
            'action': 'store_true',
        },
        'status': {
            'short': 'st',
            'help': 'client service status',
            'action': 'store_true',
        },
        'stop': {
            'short': 'S',
            'help': 'stop client service',
            'action': 'store_true'
        },
    }).set_arguments()
    if not parse_client_args(args):
        exit(1)
    exit(0)
