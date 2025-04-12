import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyvisauto",
    version="1.0.4",
    author="Minyoung Choi",
    author_email="minyoung.choi@gmail.com",
    description="pyvisauto - a vision-based automation tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mrmin123/pyvisauto",
    packages=['pyvisauto'],
    install_requires=[
        'opencv-contrib-python-headless~=4.10.0.84',
        'pillow~=11.0.0',
        'pyautogui~=0.9.54',
        'pytesseract~=0.3.13',
        'numpy~=2.2.0 ',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.11.0',
)
