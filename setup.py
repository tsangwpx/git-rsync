
from setuptools import setup, find_packages

if __name__ == '__main__':
    setup(
        name='gitrsync',
        version='0.2',
        packages=find_packages(),
        author='Aaron Tsang',
        author_email='tsangwpx@gmail.com',
        description='Transfer repository files between hosts with rsync',
        license='MIT License',
        keywords='git rsync',
    )
