from setuptools import setup, find_packages

import gitrsync

if __name__ == '__main__':
    setup(
        name='gitrsync',
        version=gitrsync.__version__,
        packages=find_packages(),
        entry_points={
            'console_scripts': [
                'git-rsync = gitrsync.__main__:main',
            ]
        },
        author='Aaron Tsang',
        author_email='tsangwpx@gmail.com',
        description='Transfer repository files between hosts with rsync',
        license='MIT License',
        keywords='git rsync',
    )
