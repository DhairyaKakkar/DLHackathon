from setuptools import find_packages, setup

setup(
    name="cvengine",
    version="0.1.0",
    description="Production-ready modular Computer Vision framework",
    author="Dhairya Kakkar",
    packages=find_packages(exclude=["tests", "examples", "scripts"]),
    python_requires=">=3.10",
    install_requires=[
        "torch>=2.0.0",
        "torchvision>=0.15.0",
        "numpy>=1.24.0",
        "opencv-python>=4.8.0",
        "Pillow>=10.0.0",
        "pyyaml>=6.0",
        "pandas>=2.0.0",
        "scipy>=1.11.0",
    ],
    extras_require={
        "api": ["fastapi>=0.100.0", "uvicorn[standard]>=0.23.0", "python-multipart>=0.0.6"],
        "dashboard": ["streamlit>=1.28.0"],
        "detection": ["ultralytics>=8.0.0"],
        "ocr": ["pytesseract>=0.3.10", "easyocr>=1.7.0"],
        "sam": ["segment-anything>=1.0"],
        "logging": ["tensorboard>=2.14.0", "wandb>=0.15.0"],
        "dev": ["pytest>=7.4.0", "ruff>=0.1.0"],
    },
)
