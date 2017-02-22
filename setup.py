from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pyrpc',
    version='0.0.1',
    description='Simple RPC client.',
    long_description=long_description,
    url='https://github.com/bkeyoumarsi/python-rpc',
    author='Bardia Keyoumarsi',
    author_email='bardia@keyoumarsi.com',
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: RPC Calls',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        # XXX check the version below
        # 'Programming Language :: Python :: 3.6',
    ],

    keywords='rpc rpc-client xdr',
    packages=['pyrpc'],
    install_requires=['six'],
)
