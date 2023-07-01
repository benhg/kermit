"""
@file setup.py
@brief the PyPI required setup.py
"""

import os
from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

version_ns = {}
with open(os.path.join("kermit_sdr", "version.py")) as f:
    exec(f.read(), version_ns)
version = version_ns['VERSION']

with open('requirements.txt') as f:
    install_requires = f.readlines()

setup(name='kermit-sdr',
      version=version,
      license='MIT',
      author="Benjamin Glick",
      author_email='glick@glick.cloud',
      classifiers=[
          "Development Status :: 3 - Alpha",
          "Intended Audience :: Science/Research",
          "License :: OSI Approved :: Apache Software License",
          "Natural Language :: English", "Operating System :: OS Independent",
          "Programming Language :: Python :: 3",
          "Topic :: Scientific/Engineering"
      ],
      python_requires=">=3.6.0",
      packages=find_packages(),
      url='https://github.com/benhg/kermit',
      keywords=["kermit", "radio", "SDR", "map", "geospatial"],
      entry_points={'console_scripts': ['kermit=kermit_sdr.kermit:main']},
      install_requires=install_requires,
      long_description=long_description,
      long_description_content_type='text/markdown'
)
