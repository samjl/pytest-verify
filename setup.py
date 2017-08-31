#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="pytest-verify",
    version='0.1.0',
    author='Sam Lea',
    author_email='samjlea@gmail.com',
    packages=find_packages(),
    include_package_data=True,
    install_requires=["pytest>=2.8.0", "pytest-loglevels>=0.3.0", "future",
                      "decorator"],
    # the following makes a plugin available to pytest
    entry_points={'pytest11': ['verify = pytest_verify.pytest_verify']},
    # custom PyPI classifier for pytest plugins
    classifiers=["Framework :: Pytest"],
)
