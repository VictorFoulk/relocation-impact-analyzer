from setuptools import setup, find_packages

setup(
    name="relocation-impact-analyzer",
    version="0.0.1",

    description='Cost and environmental impact analysis for an intra-regional office move. (academic)',
    long_description=open('README.md').read(),
    author='Victor Foulk',
    author_email='',
    url='https://github.com/VictorFoulk/',
    download_url='https://github.com/VictorFoulk/relocation-impact-analyzer',
    keywords='python',
    license='MIT License',
    classifiers=[
            "Development Status :: 2 - Pre-Alpha",
            'Intended Audience :: Developers',
            'License :: OSI Approved :: MIT License',
            'Operating System :: OS Independent',
            'Programming Language :: Python',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.3',
            'Topic :: Scientific/Engineering :: Information Analysis'
    ],
    install_requires=["Cartopy",
                    "googlemaps",
                    "matplotlib",
                    "numpy",
                    "pandas",
                    "python-dotenv",
                    "requests_toolbelt",
                    "scipy",
                    "setuptools",
                    "numpy_financial"
    ],
    packages=find_packages(),
    include_package_data=True,
)