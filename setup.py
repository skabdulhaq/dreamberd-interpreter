from setuptools import setup, find_packages

# Read the contents of the README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dreamberd-sigma", 
    version="0.6.9", 
    author="AbdulHaq",  
    author_email="dev.abdulhaq@gmail.com", 
    description="A customized fork of dreamberd interpreter", 
    long_description=long_description,  
    long_description_content_type="text/markdown",  
    url="https://github.com/skabdulhaq/dreamberd-interpreter", 
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",  
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6", 
    entry_points={
        "console_scripts": [
            "dreamberd-sigma=dreamberd.__init__:main",
        ],
    },
)
