#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'Click>=6.0',
    'pyyaml>=3.1',
    'tqdm>=4.23.4'
]

setup_requirements = [ ]

test_requirements = [ ]

setup(
    author="Keith Schulze",
    author_email='keith.schulze@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
    description="Tools to sync data from the Australian Synchrotron",
    entry_points={
        'console_scripts': [
            'asynchy=asynchy.cli:cli',
        ],
    },
    install_requires=requirements,
    license="MIT license",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='asynchy',
    name='asynchy',
    packages=find_packages(include=['asynchy']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/keithschulze/asynchy',
    version='0.1.0',
    zip_safe=False,
)
