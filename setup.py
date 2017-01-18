from setuptools import setup
from os import path, listdir

scripts = [path.join('bin', filename) for filename in os.listdir('bin')]

setup(name='sdntest',
      version='0.1',
      description='A general SDN test framework',
      url='http://github.com/snlab-freedom/sdntest',
      author='Jensen Zhang',
      author_email='jingxuan.n.zhang@gmail.com',
      long_description="""
          SDNTest is a general purpose test framework for SDN scenario.
          It allows users to define their own testcases and repeatedly
          execute them in different docker containers.
          """,
      classifiers=[
          "License :: OSI Approved :: MIT License",
          "Programming Language :: Python",
          "Development Status :: 2 - Pre-Alpha",
          "Intended Audience :: Developers",
          "Topic :: System :: Networking :: Test Framework",
          "Topic :: Utilities"
      ],
      license='MIT',
      packages=['sdntest', 'sdntest.examples'],
      install_requires=[
          'setuptools',
          'docker'
      ],
      scripts=scripts,
      zip_safe=False)
