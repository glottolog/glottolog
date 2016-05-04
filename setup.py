from setuptools import setup, find_packages


requires = [
    # list required third-party packages here
    'clldutils>=0.7',
    'pybtex',
    'latexcodec',
    'unidecode',
]

setup(
    name='pyglottolog',
    version='0.1',
    description='python package for glottolog data curation',
    long_description='',
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
    ],
    author='',
    author_email='',
    url='',
    keywords='data linguistics',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    entry_points={
        'console_scripts': ['glottolog=pyglottolog.cli:main'],
    },
    tests_require=[],
    test_suite="pyglottolog")
