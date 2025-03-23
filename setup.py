from setuptools import setup


try:
    setup(
        name='dev_share',
        version='1.0.0',
        entry_points={'console_scripts': [
            'dshare = dev_share.cli:share_parent',
            'dshare-server = dev_share.cli:share_server',
            'dshare-client = dev_share.cli:share_client',
        ]},
    )
    exit(0)
except Exception as error:
    print(f'Failed to setup package: {error}')
    exit(1)
