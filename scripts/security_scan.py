#!/usr/bin/env python3
"""
Script simple de pruebas de seguridad:
- Verificar que no hay secretos hardcodeados en el código.
- Comprobar cabeceras de seguridad (CSP, HSTS, X-Frame-Options).
"""
import os
import re
import sys
import urllib.request


def scan_secrets():
    """Buscar posibles secretos hardcodeados."""
    patterns = [
        r'--' + r'--BEGIN PRIVATE KEY-----',
        r'--' + r'--BEGIN RSA PRIVATE KEY-----',
        r'--' + r'--BEGIN OPENSSH PRIVATE KEY-----',
        r'AIza[0-9A-Za-z-_]{35}',  # Google API key
        r'sk-[0-9A-Za-z-_]{48}',   # OpenAI key
        r'AKIA[0-9A-Z]{16}',       # AWS access key
    ]
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    findings = []
    for dirpath, _, filenames in os.walk(root_dir):
        if ".git" in dirpath or "node_modules" in dirpath or ".venv" in dirpath:
            continue
        for filename in filenames:
            if filename == "security_scan.py":
                continue
            if any(filename.endswith(ext) for ext in ['.py', '.ts', '.tsx', '.js', '.json', '.env', '.yml']):
                filepath = os.path.join(dirpath, filename)
                try:
                    with open(filepath, encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        for pattern in patterns:
                            if re.search(pattern, content):
                                findings.append(f"🚨 Possible secret in {filepath}: {pattern}")
                except Exception:
                    pass
    return findings


def check_headers(url="http://localhost:8000/health"):
    """Verificar cabeceras de seguridad en la API."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            headers = dict(response.headers)
            security_headers = [
                'X-Content-Type-Options',
                'X-Frame-Options',
                'X-XSS-Protection',
                'Strict-Transport-Security',
                'Content-Security-Policy',
            ]
            for header in security_headers:
                if header not in headers and header.lower() not in headers:
                    print(f"⚠️ Missing security header: {header}")
                else:
                    val = headers.get(header) or headers.get(header.lower())
                    print(f"✅ Header {header}: {val}")
    except Exception as exc:
        print(f"⚠️ Could not connect to {url} to check headers ({exc})")


if __name__ == "__main__":
    print("🔍 Scanning for hardcoded secrets...")
    secret_findings = scan_secrets()
    if secret_findings:
        for f in secret_findings:
            print(f)
        sys.exit(1)
    else:
        print("✅ No hardcoded secrets found.")

    print("\n🔍 Checking security headers...")
    check_headers()
