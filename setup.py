import os
from setuptools import setup
from setuptools import find_packages

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as r_file:
    README = r_file.read().strip()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name="aws-image-cleanup",
    version="0.1.0",
    url="https://github.com/Harvard-ATG/aws-image-cleanup",
    description="A python command line to to clean up AMIs",
    long_description=README,
    long_description_content_type="text/markdown",
    license="License :: OSI Approved :: BSD License",
    packages=find_packages(),
    install_requires=['boto3','pyyaml'],
    include_package_data=True,
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
)