import setuptools
from looper import __version__

with open("requirements.txt", "r") as fh:
    install_requires = fh.read().splitlines()

setuptools.setup(
    name="raspberry-looper",
    version=__version__,
    author='igrek51',
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8.0',
    install_requires=install_requires,
    dependency_links=[],
    entry_points={
        "console_scripts": [
            "looper = looper.main:main",
        ],
    },
)
