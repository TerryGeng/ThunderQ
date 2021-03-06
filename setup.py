from setuptools import setup


setup(
    name="ThunderQ",
    version="0.1",
    packages=[
        'thunderq',
        'thunderq.helper',
        'thunderq.sequencer',
        'thunderq.experiment',
        'thunderq.procedures.native',
        'thunderq.cycles.native',
        'thunderq.waveforms.native',
    ],

    author="Yanda Geng",
    author_email="gengyanda16@smail.nju.edu.cn",
    description="Experiment framework designed for waveforms-centered experiment setups.",
    keywords="scientific experiment waveforms microwave control",
    platforms="any",
    install_requires=["device_repo", "matplotlib", "numpy"],
    classifiers=[
        "License :: OSI Approved :: GNU Lesser General Public License v2 "
        "or later (LGPLv2+)",
    ],
)
