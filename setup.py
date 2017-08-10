#!/usr/bin/env python
from setuptools import setup

setup(
    name="pytest-verify",
    version='0.1.0',
    author='Sam Lea',
    author_email='samjlea@gmail.com',
    py_modules=['pytest_verify'],
    install_requires=["pytest>=2.8.0", "pytest-loglevels>=0.3.0", "future"],
    # the following makes a plugin available to pytest
    entry_points={'pytest11': ['verify = pytest_verify']},
    # custom PyPI classifier for pytest plugins
    classifiers=["Framework :: Pytest"],
)
