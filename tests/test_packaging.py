"""WO-P1-697 SF-WEB-5 — Service packaging config validation tests."""
import xml.etree.ElementTree as ET
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "packaging"


class TestSystemdUnit:
    def test_service_file_exists(self):
        assert (PKG / "systemd" / "sunday-web.service").exists()

    def test_unit_section(self):
        content = (PKG / "systemd" / "sunday-web.service").read_text()
        assert "[Unit]" in content
        assert "Description=A-Sunday Conductor Web API" in content

    def test_service_binding_loopback(self):
        content = (PKG / "systemd" / "sunday-web.service").read_text()
        assert "127.0.0.1" in content or "loopback" in content.lower()

    def test_service_hardening(self):
        content = (PKG / "systemd" / "sunday-web.service").read_text()
        assert "NoNewPrivileges=true" in content
        assert "ProtectSystem=strict" in content
        assert "PrivateTmp=true" in content

    def test_restart_policy(self):
        content = (PKG / "systemd" / "sunday-web.service").read_text()
        assert "Restart=on-failure" in content


class TestLaunchdPlist:
    def test_plist_exists(self):
        assert (PKG / "launchd" / "com.a-sunday.conductor.web.plist").exists()

    def test_plist_valid_xml(self):
        tree = ET.parse(PKG / "launchd" / "com.a-sunday.conductor.web.plist")
        assert tree.getroot().tag == "plist"

    def test_plist_label(self):
        tree = ET.parse(PKG / "launchd" / "com.a-sunday.conductor.web.plist")
        label = tree.find(".//key[@text='Label']")
        if label is None:
            keys = tree.findall(".//key")
            values = tree.findall(".//string")
            for i, k in enumerate(keys):
                if k.text == "Label":
                    assert values[i].text == "com.a-sunday.conductor.web"
                    break

    def test_plist_keepalive(self):
        content = (PKG / "launchd" / "com.a-sunday.conductor.web.plist").read_text()
        assert "KeepAlive" in content
        assert "true" in content


class TestWindowsScript:
    def test_script_exists(self):
        assert (PKG / "windows" / "install-service.ps1").exists()

    def test_script_has_uninstall(self):
        content = (PKG / "windows" / "install-service.ps1").read_text()
        assert "Uninstall" in content  # param name or switch
        assert "Unregister-ScheduledTask" in content

    def test_script_validates_exe(self):
        content = (PKG / "windows" / "install-service.ps1").read_text()
        assert "Test-Path" in content
        assert "not found" in content


class TestUmbrelManifest:
    def test_manifest_exists(self):
        assert (PKG / "umbrel" / "umbrel-app.yaml").exists()

    def test_manifest_has_id(self):
        content = (PKG / "umbrel" / "umbrel-app.yaml").read_text()
        assert "id:" in content
        assert "a-sunday" in content.lower()

    def test_manifest_port(self):
        content = (PKG / "umbrel" / "umbrel-app.yaml").read_text()
        assert "8756" in content


class TestReadme:
    def test_readme_exists(self):
        assert (PKG / "README.md").exists()

    def test_readme_covers_platforms(self):
        content = (PKG / "README.md").read_text()
        for platform in ("Linux", "macOS", "Windows", "Umbrel"):
            assert platform in content

    def test_readme_has_verification(self):
        content = (PKG / "README.md").read_text()
        assert "curl" in content
        assert "health" in content
