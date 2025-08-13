#!/usr/bin/env python3
"""
Script to build Lambda layer with dependencies for the generate functions
"""

import os
import subprocess
import shutil
from pathlib import Path

def build_layer():
    """Build Lambda layer with required dependencies"""
    
    # Create layer directory
    layer_dir = Path("lambda_layer")
    python_dir = layer_dir / "python"
    
    # Clean up existing layer
    if layer_dir.exists():
        shutil.rmtree(layer_dir)
    
    # Create directories
    python_dir.mkdir(parents=True, exist_ok=True)
    
    
    print("Installing dependencies to Lambda layer...")

    # Install main dependencies
    subprocess.run([
        "pip", "install", "-r", "lambda_requirements.txt", 
        "-t", str(python_dir),
    ], check=True)
    
    # Install Pillow separately with Lambda-compatible flags
    print("Installing Pillow for Lambda compatibility...")
    subprocess.run([
        "pip", "install", "Pillow",
        "-t", str(python_dir),
        "--platform", "manylinux2014_x86_64",
        "--only-binary=:all:",
        "--implementation", "cp",
        "--python-version", "3.13",
        "--abi", "cp313",
        "--upgrade"
    ], check=True)
    
    # Install lxml separately with Lambda-compatible flags
    print("Installing lxml for Lambda compatibility...")
    subprocess.run([
        "pip", "install", "lxml",
        "-t", str(python_dir),
        "--platform", "manylinux2014_x86_64",
        "--only-binary=:all:",
        "--implementation", "cp",
        "--python-version", "3.13",
        "--abi", "cp313",
        "--upgrade"
    ], check=True)
    
    # Install lxml-html-clean separately with Lambda-compatible flags
    print("Installing lxml-html-clean for Lambda compatibility...")
    subprocess.run([
        "pip", "install", "lxml-html-clean",
        "-t", str(python_dir),
        "--platform", "manylinux2014_x86_64",
        "--only-binary=:all:",
        "--implementation", "cp",
        "--python-version", "3.13",
        "--abi", "cp313",
        "--upgrade"
    ], check=True)
    
    print(f"Lambda layer built successfully at {layer_dir}")
    return layer_dir

if __name__ == "__main__":
    build_layer() 