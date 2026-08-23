"""Tkinter desktop adapter for the A-Sunday Conductor control center.

The desktop layer consumes only the application-service snapshot/actions. It
contains no process, tunnel, Git, or persistence implementation.
"""

from __future__ import annotations

import os
import re
import sys
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Callable, Protocol

import tkinter as tk
from tkinter import filedialog, ttk
import webbrowser

from .branding import APP_NAME, APP_VERSION
from .error_explanations_en import ERROR_EXPLANATIONS_EN
from .i18n import get_language, set_language, tr
from .control_center import ControlCenterError, ControlCenterSnapshot
from .domain import WorkerState
from .lifecycle_coordinator import LifecycleCoordinatorError
from .lifecycle_executor import LifecycleExecutionResult
from .runtime_setup import RuntimeSetupError, SetupReadiness, WorkerSetupDraft
from .worker_serena_settings import (
    ENGINE_TOOLS,
    KNOWN_LANGUAGES,
    LanguageBackend,
    WorkerSerenaSettings,
)
from .local_instances import (
    InstanceHealthState,
    InstanceResultCode,
    _TUNNEL_ID_RE,
    connector_name_for_project,
)
from .config_blurbs import active_blurbs
from .memory_presence import MemoryPresenceState, inspect_memory_presence
from .upstream_check import fetch_upstream_status


def find_user_guide_path() -> Path | None:
    """Locate the bundled user guide (repo layout in dev, bundle dir frozen).

    Follows the UI language: USER-GUIDE-EN.md when English is active and
    available, otherwise the Thai USER-GUIDE.md.
    """
    from .i18n import get_language

    names = ["USER-GUIDE.md"]
    if get_language() == "en":
        names = ["USER-GUIDE-EN.md", "USER-GUIDE.md"]
    candidates: list[Path] = []
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        candidates.extend(Path(bundle) / "docs" / name for name in names)
    repo_docs = Path(__file__).resolve().parents[2] / "docs"
    candidates.extend(repo_docs / name for name in names)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _default_guide_opener(path: Path) -> None:
    os.startfile(str(path))  # noqa: S606 - opens the bundled guide in the default viewer


def find_icon_path() -> Path | None:
    """Locate the application icon (repo layout in dev, bundle dir frozen)."""
    candidates = []
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        candidates.append(Path(bundle) / "assets" / "a-conductor.ico")
    candidates.append(Path(__file__).resolve().parents[2] / "assets" / "a-conductor.ico")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


SERENA_ACTIVATION_PROMPT = "Activate the current dir as project using serena"


ERROR_EXPLANATIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "SELECT_WORKER": (
        "ยังไม่ได้เลือก Worker",
        (
            "ขาด: การคลิกเลือกแถวในตาราง WORKERS (ฝั่งขวา)",
            "ทำอย่างไร: คลิกแถว Worker หนึ่งครั้งก่อนกดปุ่มนี้",
        ),
    ),
    "WORKER_NAME_INVALID": (
        "ชื่อ Worker ห้ามว่าง",
        (
            "ขาด: ข้อความในช่องชื่อ (กรอกช่องว่างหรือช่องว่างล้วน)",
            "ทำอย่างไร: พิมพ์ชื่อที่ต้องการแสดงอย่างน้อย 1 ตัวอักษร แล้วกด บันทึก",
        ),
    ),
    "INSTANCE_CREATE_NOT_AVAILABLE": (
        "ฟีเจอร์สร้างตัวเชื่อมไม่พร้อมใช้งาน",
        (
            "ขาด: บริการสร้างตัวเชื่อมในเวอร์ชันที่รันอยู่",
            "ทำอย่างไร: อัปเดตโปรแกรมเป็นเวอร์ชันล่าสุดแล้วลองใหม่",
        ),
    ),
    "INSTANCE_FIELDS_REQUIRED": (
        "กรอกข้อมูลไม่ครบ",
        (
            "ขาด: ชื่อตัวเชื่อม หรือ พาธโปรเจกต์",
            "ทำอย่างไร: กรอกทั้งสองช่อง (ชื่อภาษาอังกฤษ + พาธโฟลเดอร์โปรเจกต์เต็ม)",
        ),
    ),
    "NAME_INVALID": (
        "ชื่อตัวเชื่อมไม่ถูกต้อง",
        (
            "ขาด: ชื่อต้องเป็นภาษาอังกฤษตัวพิมพ์เล็ก/ตัวเลข/ขีดกลาง เช่น research",
            "ทำอย่างไร: ห้ามมีช่องว่างหรืออักขระพิเศษ — ใช้คำเดียวเช่น research หรือ chat-beta",
        ),
    ),
    "NAME_ALREADY_EXISTS": (
        "ชื่อนี้ถูกใช้แล้ว",
        (
            "ขาด: ชื่อที่ไม่ซ้ำกับตัวเชื่อมที่มีอยู่",
            "ทำอย่างไร: เลือกชื่ออื่น หรือกด Rescan เพื่อดูรายชื่อปัจจุบันก่อน",
        ),
    ),
    "PROJECT_NOT_FOUND": (
        "ไม่พบโฟลเดอร์โปรเจกต์",
        (
            "ขาด: พาธโปรเจกต์ที่มีอยู่จริงในเครื่อง",
            "ทำอย่างไร: ตรวจพาธให้ครบ เช่น A:\\GitHub\\my-project (ต้องเป็นโฟลเดอร์จริง)",
        ),
    ),
    "TUNNEL_ID_INVALID": (
        "รูปแบบ Tunnel ID ไม่ถูกต้อง",
        (
            "ขาด: ID ขึ้นต้นด้วย tunnel_ ตามด้วยตัวเลข/อักษร 32 ตัว",
            "ทำอย่างไร: คัดลอกใหม่จาก OpenAI Platform หรือเว้นว่างไว้แล้วใส่ทีหลัง",
        ),
    ),
    "REFERENCE_MISSING": (
        "ไม่พบตัวเชื่อมต้นแบบ",
        (
            "ขาด: อย่างน้อย 1 ตัวเชื่อมที่ผ่านการตรวจสอบใน C:\\AI\\serena-instances",
            "ทำอย่างไร: สร้างตัวเชื่อมแรกตามคู่มือก่อน แล้วจึงใช้ปุ่มนี้เพิ่มตัวถัดไป",
        ),
    ),
    "INSTANCE_RENAME_NOT_AVAILABLE": (
        "การแก้ชื่อตัวเชื่อมไม่พร้อมใช้งาน",
        (
            "ขาด: บริการแก้ชื่อในเวอร์ชันที่รันอยู่",
            "ทำอย่างไร: อัปเดตโปรแกรมเป็นเวอร์ชันล่าสุดแล้วลองใหม่",
        ),
    ),
    "INSTANCE_DELETE_NOT_AVAILABLE": (
        "การลบตัวเชื่อมไม่พร้อมใช้งาน",
        (
            "ขาด: บริการลบในเวอร์ชันที่รันอยู่",
            "ทำอย่างไร: อัปเดตโปรแกรมเป็นเวอร์ชันล่าสุดแล้วลองใหม่",
        ),
    ),
    "INSTANCE_STOP_REQUIRED": (
        "ต้องหยุดตัวเชื่อมก่อนจึงจะลบได้",
        (
            "ขาด: ตัวเชื่อมยังหยุดไม่สำเร็จ (อาจกำลังทำงานอยู่)",
            "ทำอย่างไร: กด Stop รอจนสถานะเป็น STOPPED แล้วลองลบใหม่ หรือดู log ของตัวเชื่อมนั้น",
        ),
    ),
    "INSTANCE_BACKUP_FAILED": (
        "สำรองข้อมูลก่อนลบไม่สำเร็จ",
        (
            "ขาด: ไฟล์ zip สำรองไม่ถูกสร้าง (ดิสก์เต็มหรือพาธเขียนไม่ได้)",
            "ทำอย่างไร: ตรวจพื้นที่ดิสก์และโฟลเดอร์ instance-backups แล้วลองใหม่ — ยังไม่มีอะไรถูกลบ",
        ),
    ),
    "INSTANCE_DELETE_FAILED": (
        "ลบโฟลเดอร์ตัวเชื่อมไม่สำเร็จ",
        (
            "ขาด: สิทธิ์เขียน/ไฟล์ถูกโปรแกรมอื่นล็อกอยู่",
            "ทำอย่างไร: ปิดหน้าต่างหรือโปรแกรมที่เปิดไฟล์ในโฟลเดอร์นั้นแล้วลองใหม่ (สำเนาสำรอง zip ถูกเก็บไว้แล้ว)",
        ),
    ),
    "SELECT_PROJECT": (
        "ยังไม่ได้เลือกโปรเจกต์",
        (
            "ขาด: การคลิกรายการในกล่อง PROJECTS (ฝั่งซ้าย)",
            "ทำอย่างไร: เลือกโปรเจกต์ แล้วเลือก Worker ปลายทาง แล้วกด Assign",
        ),
    ),
    "SELECT_INSTANCE": (
        "ยังไม่ได้เลือกตัวเชื่อม (Connector)",
        (
            "ขาด: การคลิกแถวในแถบ CONNECTORS",
            "ทำอย่างไร: คลิกตัวเชื่อมที่ต้องการก่อนกดปุ่ม",
        ),
    ),
    "INSTANCES_NOT_AVAILABLE": (
        "ยังไม่พบตัวเชื่อมในเครื่องนี้",
        (
            "ขาด: โฟลเดอร์ตัวเชื่อมตามโครงสร้างมาตรฐาน (C:/AI/serena-instances)",
            "ทำอย่างไร: อ่านคู่มือหมวด 7 หรือกด Rescan หลังสร้างตัวเชื่อมใหม่",
        ),
    ),
    "INSTANCE_REFRESH_FAILED": (
        "โหลดสถานะตัวเชื่อมไม่สำเร็จ",
        (
            "สาเหตุที่พบบ่อย: โฟลเดอร์ตัวเชื่อมถูกย้ายหรือลบระหว่างทาง",
            "ทำอย่างไร: กด Rescan ถ้ายังไม่หาย ลองปิด-เปิดโปรแกรม",
        ),
    ),
    "INSTANCE_ACTION_FAILED": (
        "สั่งงานตัวเชื่อมไม่สำเร็จ",
        (
            "ดูรายละเอียดล่าสุดในแถบ ACTIVITY / LOG",
            "ทำอย่างไร: ลองอีกครั้ง ถ้าซ้ำให้ตรวจ log ของตัวเชื่อมนั้นในโฟลเดอร์ logs",
        ),
    ),
    "INSTANCE_START_ALL_FAILED": (
        "เปิดทั้งหมดไม่สำเร็จบางตัว",
        (
            "ดูว่าตัวไหน fail ในแถบ ACTIVITY / LOG",
            "ทำอย่างไร: เริ่มเฉพาะตัวนั้นใหม่",
        ),
    ),
    "INSTANCE_FLAG_FAILED": (
        "บันทึกค่า Auto ไม่สำเร็จ",
        (
            "สาเหตุที่พบบ่อย: ฐานข้อมูลถูกเปิดค้างด้วยอีกโปรแกรม",
            "ทำอย่างไร: ปิดโปรแกรมซ้ำแล้วลองใหม่",
        ),
    ),
    "UPSTREAM_CHECK_FAILED": (
        "เช็คอัปเดทไม่สำเร็จ",
        ("สาเหตุที่พบบ่อย: ไม่มีอินเทอร์เน็ต หรือ GitHub ไม่ตอบ", "ทำอย่างไร: ลองใหม่อีกครั้ง หรือเปิดลิงก์ในคู่มือด้วยตัวเอง"),
    ),
    "REBIND_NOT_AVAILABLE": (
        "ระบบเปลี่ยนโปรเจกต์ยังไม่พร้อม",
        ("เกิดเมื่อ service ยังไม่ถูกเชื่อม (กรณีทดสอบ)",),
    ),
    "REBIND_FAILED": (
        "เปลี่ยนโปรเจกต์ไม่สำเร็จ",
        ("ดูรายละเอียดใน ACTIVITY / LOG", "ไฟล์เดิมถูกสำรองเป็น .bak ไว้แล้ว"),
    ),
    "PREFERENCES_NOT_AVAILABLE": (
        "ระบบการตั้งค่ารวมยังไม่พร้อม",
        ("เกิดเมื่อ service ตั้งค่ายังไม่ถูกเชื่อม (กรณีทดสอบ)", "ในโปรแกรมปกติไม่ควรเจอ"),
    ),
    "PREFERENCES_LOAD_FAILED": (
        "โหลดค่าตั้งรวมไม่ได้",
        ("ลองปิด-เปิดหน้าต่างตั้งค่าใหม่", "ถ้าซ้ำให้ตรวจฐานข้อมูล"),
    ),
    "PREFERENCE_SAVE_FAILED": (
        "บันทึกค่าตั้งรวมไม่สำเร็จ",
        ("สาเหตุที่พบบ่อย: ฐานข้อมูลถูกล็อก", "ทำอย่างไร: ปิดโปรแกรมซ้ำแล้วลองใหม่"),
    ),
    "TUNNEL_SETUP_NOT_AVAILABLE": (
        "ระบบตั้ง Tunnel ID ยังไม่พร้อม",
        (
            "เกิดเมื่อ service ภายในยังไม่ถูกเชื่อม (กรณีทดสอบ)",
            "ในโปรแกรมปกติไม่ควรเจอ",
        ),
    ),
    "CONNECTOR_MATCH_MISSING": (
        "หาตัวเชื่อมที่ตรงกับโปรเจกต์ไม่เจอ",
        (
            "ขาด: ตัวเชื่อมที่ผูกกับ path โปรเจกต์เดียวกัน",
            "ทำอย่างไร: ดูคอลัมน์ CONNECTOR ในตาราง WORKERS ว่าเป็น '-' หรือไม่",
        ),
    ),
    "SETTINGS_NOT_AVAILABLE": (
        "ระบบตั้งค่ายังไม่พร้อม",
        (
            "เกิดเมื่อ service ตั้งค่ายังไม่ถูกเชื่อม (กรณีทดสอบ)",
            "ในโปรแกรมปกติไม่ควรเจอ",
        ),
    ),
    "SETTINGS_INVALID": (
        "ค่าที่กรอกยังไม่ถูกต้อง",
        (
            "ขาดหรือผิด: อย่างน้อยหนึ่งช่อง เช่น Fixed tools ห้ามใช้ร่วมกับช่องอื่น หรือชื่อ tool มีช่องว่าง",
            "ดูข้อความ ERROR สีแดงในหน้าต่างตั้งค่าปัจจุบัน",
        ),
    ),
    "SETTINGS_LANGUAGE_BACKEND_INVALID": (
        "ค่า Language backend ไม่ถูก",
        (
            "เลือกได้แค่ LSP หรือ JetBrains จากรายการ",
        ),
    ),
    "SETTINGS_TOOL_TIMEOUT_INVALID": (
        "ค่า Tool timeout ไม่ใช่ตัวเลข",
        (
            "กรอกเป็นตัวเลขวินาที 1-86400",
        ),
    ),
    "SETTINGS_LOAD_FAILED": (
        "โหลดค่าตั้งเข้าไม่ได้",
        (
            "ลองปิด-เปิดหน้าต่างตั้งค่าใหม่",
            "ถ้าซ้ำให้ตรวจฐานข้อมูล",
        ),
    ),
    "SETTINGS_SAVE_FAILED": (
        "บันทึกค่าตั้งไม่สำเร็จ",
        (
            "สาเหตุที่พบบ่อย: ฐานข้อมูลถูกล็อก",
            "ทำอย่างไร: ปิดโปรแกรมซ้ำแล้วลองใหม่",
        ),
    ),
    "SETTINGS_RESULT_INVALID": (
        "ผลลัพธ์จากระบบผิดรูปแบบ",
        (
            "กรณีภายใน",
            "ลองใหม่อีกครั้ง",
        ),
    ),
    "CLIPBOARD_COPY_FAILED": (
        "คัดลอกข้อความไม่สำเร็จ",
        (
            "Clipboard ของ Windows ไม่พร้อมใช้งานในขณะนี้",
            "ทำอย่างไร: ลองกด Activate ใหม่อีกครั้ง",
        ),
    ),
    "GUIDE_NOT_FOUND": (
        "ไม่พบไฟล์คู่มือ",
        (
            "ขาด: docs/USER-GUIDE.md ในตำแหน่งติดตั้ง",
            "ทำอย่างไร: ติดตั้งแอปใหม่ด้วย setup.exe",
        ),
    ),
    "GUIDE_OPEN_FAILED": (
        "เปิดคู่มือไม่สำเร็จ",
        (
            "ลองปิด-เปิดโปรแกรมแล้วกด คู่มือ อีกครั้ง",
        ),
    ),
    "LIFECYCLE_NOT_WIRED": (
        "ระบบสั่ง Worker ยังไม่ถูกเชื่อม",
        (
            "ปกติไม่ควรเจอ",
            "รีสตาร์ทโปรแกรม",
        ),
    ),
    "LIFECYCLE_COMMAND_FAILED": (
        "สั่งงาน Worker ล้มเหลว",
        (
            "ดู log ล่าสุดใน ACTIVITY / LOG",
        ),
    ),
    "LIFECYCLE_RESULT_INVALID": (
        "ผลลัพธ์ Worker ผิดรูปแบบ",
        (
            "ลองสั่งใหม่อีกครั้ง",
        ),
    ),
    "RUNTIME_SETUP_NOT_AVAILABLE": (
        "ระบบ Setup ยังไม่พร้อม",
        (
            "ปกติไม่ควรเจอ",
            "รีสตาร์ทโปรแกรม",
        ),
    ),
    "RUNTIME_SETUP_FAILED": (
        "เปิดหน้า Setup ไม่สำเร็จ",
        (
            "ลองเลือก Worker ใหม่แล้วกด Setup อีกครั้ง",
        ),
    ),
    "RUNTIME_SETUP_RESULT_INVALID": (
        "ข้อมูล Setup ผิดรูปแบบ",
        (
            "ลองเปิดหน้า Setup ใหม่",
        ),
    ),
    "RUNTIME_SETUP_SAVE_FAILED": (
        "บันทึก Setup ไม่สำเร็จ",
        (
            "ตรวจว่า path ที่กรอกมีจริงและเขียนได้",
        ),
    ),
    "HEALTH_PORT_INVALID": (
        "Port ไม่ถูกต้อง",
        (
            "กรอกเป็นตัวเลข 1-65535 และไม่ชนกับตัวอื่น",
        ),
    ),
    "PROJECT_IDENTITY_SAVE_FAILED": (
        "บันทึก identity โปรเจกต์ไม่สำเร็จ",
        (
            "ลองกด Capture อีกครั้ง",
            "ถ้าซ้ำตรวจสิทธิ์โฟลเดอร์",
        ),
    ),
    "CONTROL_CENTER_START_FAILED": (
        "เปิดระบบไม่สำเร็จ",
        (
            "ตรวจสิทธิ์เขียนฐานข้อมูล",
            "ดูคู่มือหมวด 8",
        ),
    ),
    "WORKER_BUSY": (
        "Worker กำลังทำงานอยู่",
        (
            "ขาด: Worker ต้องหยุดและไม่มีโปรเจกต์แล้วเท่านั้น",
            "ทำอย่างไร: กด Stop แล้ว Release โปรเจกต์ออกก่อน แล้วลองใหม่",
        ),
    ),
    "PORT_INVALID": (
        "พอร์ตไม่ถูกต้อง",
        (
            "ขาด: พอร์ตต้องเป็นเลข 1-65535 และไม่ชนกับตัวอื่น",
            "ทำอย่างไร: เลือกพอร์ตว่างถัดไป (ค่าเริ่มต้นคือ 18010 + หมายเลข worker)",
        ),
    ),
    "INSTANCE_NOT_FOUND": (
        "ไม่พบตัวเชื่อมนี้",
        (
            "ขาด: ตัวเชื่อมอาจถูกลบหรือย้ายไปแล้ว",
            "ทำอย่างไร: กด Rescan เพื่อค้นหาใหม่ แล้วเลือกรายการใหม่",
        ),
    ),
    "INSTANCE_OUTSIDE_ROOT": (
        "ตัวเชื่อมอยู่นอกพื้นที่ควบคุม",
        (
            "ขาด: โฟลเดอร์ตัวเชื่อมต้องอยู่ใต้ C:\\AI\\serena-instances เท่านั้น",
            "ทำอย่างไร: ย้ายกลับเข้าโฟลเดอร์หลักก่อนดำเนินการ",
        ),
    ),
    "INSTANCE_NAME_INVALID": (
        "ชื่อตัวเชื่อมไม่ถูกต้อง",
        (
            "ขาด: ชื่อต้องเป็นอังกฤษพิมพ์เล็ก/ตัวเลข/ขีดกลางเท่านั้น",
            "ทำอย่างไร: ตรวจชื่อที่กรอกแล้วลองใหม่",
        ),
    ),
    "INSTANCE_DISPLAY_NAME_INVALID": (
        "ชื่อที่แสดงห้ามว่าง",
        (
            "ขาด: ข้อความในช่องชื่อ",
            "ทำอย่างไร: พิมพ์ชื่ออย่างน้อย 1 ตัวอักษรแล้วบันทึกใหม่",
        ),
    ),
    "REFERENCE_PS1_INVALID": (
        "ไฟล์ instance.ps1 ของต้นแบบไม่ถูกต้อง",
        (
            "ขาด: บรรทัด $TunnelClientPath / $LegacySecretPath ในต้นแบบ",
            "ทำอย่างไร: เลือกต้นแบบตัวอื่น หรือซ่อม instance.ps1 ของต้นแบบก่อน",
        ),
    ),
    "REFERENCE_SCRIPT_MISSING": (
        "สคริปต์ของต้นแบบไม่ครบ",
        (
            "ขาด: start.ps1 หรือ stop.ps1 ในโฟลเดอร์ต้นแบบ",
            "ทำอย่างไร: ใช้ตัวเชื่อมที่สมบูรณ์เป็นต้นแบบ",
        ),
    ),
    "REFERENCE_CMD_MISSING": (
        "ไฟล์ Start/Stop .cmd ของต้นแบบไม่ครบ",
        (
            "ขาด: Start-*.cmd หรือ Stop-*.cmd ในโฟลเดอร์ต้นแบบ",
            "ทำอย่างไร: ใช้ตัวเชื่อมที่สมบูรณ์เป็นต้นแบบ",
        ),
    ),
    "REFERENCE_TEMPLATE_MISSING": (
        "แม่แบบ profile ของต้นแบบไม่ครบ",
        (
            "ขาด: ไฟล์ profiles/*.yaml.template หรือ serena_config.yml",
            "ทำอย่างไร: ใช้ตัวเชื่อมที่สมบูรณ์เป็นต้นแบบ",
        ),
    ),
    "CREATE_VERIFY_FAILED": (
        "สร้างแล้วแต่ตรวจไม่พบตัวใหม่",
        (
            "ขาด: ผลการค้นหาหลังสร้างไม่ตรงกับที่คาด",
            "ทำอย่างไร: กด Rescan ดูรายการใหม่ หรือลองสร้างใหม่ด้วยชื่ออื่น",
        ),
    ),
    "INSTANCE_CREATE_FAILED": (
        "สร้างตัวเชื่อมไม่สำเร็จ",
        (
            "ขาด: สาเหตุเชิงระบบไฟล์ (ดิสก์/สิทธิ์)",
            "ทำอย่างไร: ดูข้อความใน ACTIVITY / LOG แล้วลองใหม่",
        ),
    ),
    "INSTANCE_RENAME_FAILED": (
        "เปลี่ยนชื่อที่แสดงไม่สำเร็จ",
        (
            "ขาด: การเขียนลงฐานข้อมูลล้มเหลว",
            "ทำอย่างไร: ลองใหม่อีกครั้ง หรือรีสตาร์ตโปรแกรมแล้วลอง",
        ),
    ),
    "GENERIC": (
        "เกิดข้อผิดพลาด",
        (
            "ดูโค้ดด้านบนและ log ใน ACTIVITY / LOG",
            "ถ้าซ้ำๆ ให้ปิด-เปิดโปรแกรม",
        ),
    ),
}


class RowPathTip:
    """Hover tooltip showing the full path of the tree row under the cursor."""

    def __init__(self, tree, provider, theme: "DesktopTheme") -> None:
        self.tree = tree
        self.provider = provider
        self.theme = theme
        self.tip: tk.Toplevel | None = None
        self._after = None
        tree.bind("<Motion>", self._on_motion, add="+")
        tree.bind("<Leave>", self._hide, add="+")

    def _on_motion(self, event) -> None:
        row = self.tree.identify_row(event.y)
        if not row:
            self._hide()
            return
        self._hide()
        path = self.provider(row)
        if not path:
            return
        self._after = self.tree.after(
            450, lambda: self._show(event.x_root, event.y_root, path)
        )

    def _show(self, x: int, y: int, path: str) -> None:
        self.tip = window = tk.Toplevel(self.tree)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x + 14}+{y + 16}")
        tk.Label(
            window,
            text=path,
            bg="#1c1f26",
            fg="#e6e6e6",
            justify="left",
            font=(self.theme.monospace_font, 9),
            padx=8,
            pady=5,
        ).pack()

    def _hide(self, _event=None) -> None:
        if self._after is not None:
            self.tree.after_cancel(self._after)
            self._after = None
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


class ToolTip:
    """Minimal hover tooltip (no shortcuts, works for every widget)."""

    def __init__(self, widget, text: str, theme: "DesktopTheme") -> None:
        self.widget = widget
        self.text = text
        self.theme = theme
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        if self.tip is not None or not self.text or not self.text.strip():
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            window,
            text=self.text,
            bg="#1c1f26",
            fg="#e6e6e6",
            justify="left",
            font=(self.theme.monospace_font, 9),
            padx=8,
            pady=5,
        ).pack()

    def _hide(self, _event=None) -> None:
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


_URL_RE = re.compile(r"https?://[^\s)]+")


def link_url_spans(text: str) -> tuple[tuple[int, int], ...]:
    """Return (start, end) character spans of http(s) URLs inside text."""
    return tuple((m.start(), m.end()) for m in _URL_RE.finditer(text))


def _attach_tip(widget, text: str, theme: "DesktopTheme"):
    widget._acond_tooltip = ToolTip(widget, text, theme)
    return widget


class ControlCenterUIService(Protocol):
    def snapshot(self) -> ControlCenterSnapshot: ...

    def register_project(
        self,
        root_path,
        *,
        display_name: str | None = None,
        project_id: str | None = None,
    ): ...

    def assign_project(
        self,
        worker_id: str,
        project_id: str,
        *,
        mutation_allowed: bool = True,
    ): ...

    def release_worker(self, worker_id: str): ...


@dataclass(frozen=True, slots=True)
class DesktopTheme:
    background: str = "#0c1015"
    panel: str = "#121820"
    panel_alt: str = "#171f29"
    border: str = "#263241"
    foreground: str = "#d7e0ea"
    muted: str = "#7f8c9a"
    accent: str = "#5cc8d7"
    ready: str = "#62d394"
    ready_dim: str = "#2f6b4a"
    warning: str = "#e6b85c"
    error: str = "#ee6b73"
    idle: str = "#87929d"
    selection: str = "#20394a"
    monospace_font: str = "Cascadia Mono"
    sans_font: str = "Segoe UI"
    base_font_size: int = 10


class AConductorDesktopApp:
    def __init__(
        self,
        root: tk.Tk,
        *,
        service: ControlCenterUIService,
        theme: DesktopTheme | None = None,
        directory_picker: Callable[[], str] | None = None,
        error_handler: Callable[[str], None] | None = None,
        background_executor: Executor | None = None,
        guide_opener: Callable[[Path], None] | None = None,
    ) -> None:
        self.root = root
        self.service = service
        self.theme = theme or DesktopTheme()
        self._directory_picker = directory_picker or filedialog.askdirectory
        self._error_handler = error_handler or self._show_error
        self._guide_opener = guide_opener
        self._background_executor = background_executor or ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="a-conductor-ui"
        )
        self._owns_background_executor = background_executor is None
        self._project_ids: list[str] = []
        self._project_paths: dict[str, str] = {}
        self._worker_ids: dict[str, str] = {}
        self._setup_entries: dict[str, ttk.Entry] = {}
        self._setup_draft: WorkerSetupDraft | None = None
        self._instance_rows: dict[str, str] = {}
        self._row_path_tip_providers: dict = {}
        self._monitor_instances: dict = {}

        self._configure_root()
        self._configure_styles()
        self._build_layout()
        self.refresh()

    def _configure_root(self) -> None:
        pref_getter = getattr(self.service, "get_preference", None)
        if callable(pref_getter):
            try:
                if pref_getter("language"):
                    set_language("en")
            except Exception:
                pass
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_request)
        self.root.configure(background=self.theme.background)
        self.root.geometry("1080x680")
        self.root.minsize(980, 640)
        icon = find_icon_path()
        if icon is not None:
            try:
                self.root.iconbitmap(str(icon))
            except tk.TclError:
                pass

    def _configure_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "AConductor.TButton",
            background=self.theme.panel_alt,
            foreground=self.theme.foreground,
            bordercolor=self.theme.border,
            focusthickness=1,
            focuscolor=self.theme.accent,
            padding=(9, 5),
            font=(self.theme.sans_font, self.theme.base_font_size),
        )
        style.map(
            "AConductor.TButton",
            background=[("active", self.theme.selection), ("disabled", self.theme.panel)],
            foreground=[("disabled", self.theme.muted)],
        )
        style.configure(
            "Workers.Treeview",
            background=self.theme.panel,
            fieldbackground=self.theme.panel,
            foreground=self.theme.foreground,
            bordercolor=self.theme.border,
            rowheight=28,
            font=(self.theme.monospace_font, self.theme.base_font_size),
        )
        style.configure(
            "Workers.Treeview.Heading",
            background=self.theme.panel_alt,
            foreground=self.theme.muted,
            bordercolor=self.theme.border,
            font=(self.theme.sans_font, self.theme.base_font_size, "bold"),
        )
        style.map(
            "Workers.Treeview",
            background=[("selected", self.theme.selection)],
            foreground=[("selected", self.theme.foreground)],
        )

    def _build_layout(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=3)
        self.root.grid_rowconfigure(4, weight=2)

        top = tk.Frame(
            self.root,
            bg=self.theme.panel,
            highlightthickness=1,
            highlightbackground=self.theme.border,
        )
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        top.grid_columnconfigure(1, weight=1)
        tk.Label(
            top,
            text="A-CONDUCTOR",
            bg=self.theme.panel,
            fg=self.theme.foreground,
            font=(self.theme.monospace_font, 14, "bold"),
            padx=12,
            pady=9,
        ).grid(row=0, column=0, sticky="w")
        tk.Label(
            top,
            text="",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        ).grid(row=0, column=1, sticky="e", padx=12)
        self.connection_label = tk.Label(
            top,
            text="● ONLINE",
            bg=self.theme.panel,
            fg=self.theme.ready,
            font=(self.theme.monospace_font, 10, "bold"),
            padx=12,
        )
        self.connection_label.grid(row=0, column=2, sticky="e")
        _attach_tip(
            self.connection_label,
            "ONLINE = ฐานข้อมูลควบคุมเชื่อมถึงได้ (local)\nOFFLINE (สีแดง) = service ตอบสนองไม่ได้",
            self.theme,
        )
        self.help_button = self._button(top, tr("btn.guide"), self.open_guide)
        self.help_button.grid(row=0, column=3, sticky="e", padx=(0, 4), pady=6)
        _attach_tip(self.help_button, tr("tip.guide"), self.theme)
        self.prefs_button = self._button(top, tr("btn.settings"), self.open_preferences)
        self.prefs_button.grid(row=0, column=4, sticky="e", padx=(0, 8), pady=6)
        _attach_tip(self.prefs_button, tr("tip.settings"), self.theme)
        if not all(
            callable(getattr(self.service, name, None))
            for name in ("get_preference", "set_preference")
        ):
            self.prefs_button.state(["disabled"])

        hint = tk.Label(
            self.root,
            text=tr("hint.three.steps"),
            bg=self.theme.background,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
            anchor="w",
        )
        hint.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 2))

        body = tk.Frame(self.root, bg=self.theme.background)
        body.grid(row=2, column=0, sticky="nsew", padx=10, pady=0)
        body.grid_columnconfigure(0, weight=0, minsize=280)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        project_panel = self._panel(body, "PROJECTS")
        project_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        project_panel.grid_rowconfigure(1, weight=1)
        project_panel.grid_columnconfigure(0, weight=1)
        self.project_list = tk.Listbox(
            project_panel,
            bg=self.theme.panel,
            fg=self.theme.foreground,
            selectbackground=self.theme.selection,
            selectforeground=self.theme.foreground,
            borderwidth=0,
            highlightthickness=0,
            activestyle="none",
            exportselection=False,
            font=(self.theme.monospace_font, self.theme.base_font_size),
        )
        project_scroll = ttk.Scrollbar(project_panel, orient="vertical", command=self.project_list.yview)
        self.project_list.configure(yscrollcommand=project_scroll.set)
        self.project_list.grid(row=1, column=0, sticky="nsew", padx=(9, 0), pady=(0, 4))
        project_scroll.grid(row=1, column=1, sticky="ns", padx=(0, 9), pady=(0, 4))

        project_actions = tk.Frame(project_panel, bg=self.theme.panel)
        project_actions.grid(row=2, column=0, columnspan=2, sticky="ew", padx=9, pady=(0, 9))
        self.add_button = self._button(project_actions, "Add Project", self.add_project)
        _attach_tip(self.add_button, "เพิ่มโปรเจกต์จากโฟลเดอร์ในเครื่อง (ไม่แตะไฟล์ในโปรเจกต์)", self.theme)
        self.assign_button = self._button(project_actions, "Assign", self.assign_selected)
        _attach_tip(self.assign_button, "ย้ายโปรเจกต์ที่เลือกไปยัง Worker ที่เลือก (เลือก Worker ทางขวาก่อน)", self.theme)
        self.activate_button = self._button(project_actions, "Activate", self.copy_activation_prompt)
        _attach_tip(
            self.activate_button,
            "คัดลอก prompt สำหรับ activate โปรเจกต์ที่เลือก แล้วนำไปวางใน AI chat ที่เชื่อม Serena",
            self.theme,
        )
        for index, button in enumerate((self.add_button, self.assign_button, self.activate_button)):
            button.grid(row=0, column=index, padx=(0, 6), sticky="w")

        self.memory_status_label = tk.Label(
            project_panel,
            text="สมองโปรเจกต์: เลือกโปรเจกต์เพื่อดูสถานะ",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 8),
            anchor="w",
            justify="left",
            wraplength=250,
        )
        self.memory_status_label.grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=9, pady=(0, 8)
        )
        _attach_tip(
            self.memory_status_label,
            "ตรวจสอบแบบอ่านอย่างเดียว: มีความจำ Serena ในโปรเจกต์นี้หรือไม่\nถ้ายังไม่มี onboarding จะทำงานเมื่อ agent เข้าโปรเจกต์ครั้งแรก\nและควรเริ่มบทสนทนาใหม่หลัง onboarding จบ",
            self.theme,
        )
        self.project_list.bind(
            "<<ListboxSelect>>", lambda _event: self._refresh_memory_status()
        )

        worker_panel = self._panel(body, "WORKERS")
        worker_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        worker_panel.grid_rowconfigure(1, weight=1)
        worker_panel.grid_columnconfigure(0, weight=1)
        columns = ("worker", "state", "project", "path", "connector")
        self.worker_tree = ttk.Treeview(
            worker_panel,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Workers.Treeview",
        )
        headings = {
            "worker": ("WORKER", 120),
            "state": ("STATE", 90),
            "project": ("PROJECT", 170),
            "path": ("PATH", 260),
            "connector": ("CONNECTOR", 150),
        }
        for name, (label, width) in headings.items():
            self.worker_tree.heading(name, text=label, anchor="w")
            self.worker_tree.column(name, width=width, minwidth=80, anchor="w")
        worker_scroll = ttk.Scrollbar(worker_panel, orient="vertical", command=self.worker_tree.yview)
        self.worker_tree.configure(yscrollcommand=worker_scroll.set)
        self.worker_tree.grid(row=1, column=0, sticky="nsew", padx=(9, 0), pady=(0, 5))
        worker_scroll.grid(row=1, column=1, sticky="ns", padx=(0, 9), pady=(0, 5))
        self.worker_xscroll = ttk.Scrollbar(
            worker_panel, orient="horizontal", command=self.worker_tree.xview
        )
        self.worker_tree.configure(xscrollcommand=self.worker_xscroll.set)
        self.worker_xscroll.grid(row=2, column=0, sticky="ew", padx=(9, 0), pady=(0, 4))
        self.worker_tree.bind("<<TreeviewSelect>>", lambda _event: self._update_lifecycle_buttons())
        self.worker_tree.tag_configure("ready", foreground=self.theme.ready)
        self.worker_tree.tag_configure("warning", foreground=self.theme.warning)
        self.worker_tree.tag_configure("error", foreground=self.theme.error)
        self.worker_tree.tag_configure("idle", foreground=self.theme.idle)
        self._attach_row_path_tip(self.worker_tree, column=3, label=tr("menu.copy.path"))

        actions = tk.Frame(worker_panel, bg=self.theme.panel)
        actions.grid(row=3, column=0, columnspan=2, sticky="ew", padx=9, pady=(4, 9))
        self.release_button = self._button(actions, "Release", self.release_selected)
        _attach_tip(self.release_button, tr("tip.release"), self.theme)
        self.refresh_button = self._button(actions, "Refresh", self.refresh)
        _attach_tip(self.refresh_button, tr("tip.refresh"), self.theme)
        self.start_button = self._button(actions, "Start", self.start_selected)
        _attach_tip(self.start_button, tr("tip.start"), self.theme)
        self.stop_button = self._button(actions, "Stop", self.stop_selected)
        _attach_tip(self.stop_button, tr("tip.stop"), self.theme)
        self.restart_button = self._button(actions, "Restart", self.restart_selected)
        _attach_tip(self.restart_button, tr("tip.restart"), self.theme)
        self.setup_button = self._button(actions, "Setup", self.open_runtime_setup)
        _attach_tip(self.setup_button, tr("tip.setup"), self.theme)
        self.config_button = self._button(actions, "Config", self.open_worker_config)
        _attach_tip(self.config_button, tr("tip.config"), self.theme)
        self.add_worker_button = self._button(actions, "+ Worker", self.open_add_worker_dialog)
        _attach_tip(
            self.add_worker_button,
            tr("tip.add.worker"),
            self.theme,
        )
        self.rename_worker_button = self._button(actions, "Rename", self.open_rename_worker_dialog)
        _attach_tip(self.rename_worker_button, tr("tip.rename.worker"), self.theme)
        self.delete_worker_button = self._button(actions, "Delete", self.delete_selected_worker)
        _attach_tip(
            self.delete_worker_button,
            tr("tip.delete.worker"),
            self.theme,
        )
        for index, button in enumerate(
            (
                self.release_button,
                self.refresh_button,
                self.start_button,
                self.stop_button,
                self.restart_button,
                self.setup_button,
                self.config_button,
                self.add_worker_button,
                self.rename_worker_button,
                self.delete_worker_button,
            )
        ):
            button.grid(row=index // 4, column=index % 4, padx=(0, 6), pady=(0, 3), sticky="w")
        self.start_button.state(["disabled"])
        self.stop_button.state(["disabled"])
        self.restart_button.state(["disabled"])
        self.setup_button.state(["disabled"])
        self.config_button.state(["disabled"])

        instances_panel = self._panel(self.root, "CONNECTORS")
        instances_panel.grid(row=3, column=0, sticky="ew", padx=10, pady=(6, 0))
        instances_panel.grid_columnconfigure(0, weight=1)
        instance_columns = ("name", "port", "state", "project", "tunnel", "auto")
        self.instance_tree = ttk.Treeview(
            instances_panel,
            columns=instance_columns,
            show="headings",
            selectmode="browse",
            style="Workers.Treeview",
            height=3,
        )
        instance_headings = {
            "name": ("INSTANCE", 150),
            "port": ("PORT", 80),
            "state": ("STATE", 80),
            "project": ("PROJECT", 280),
            "tunnel": ("TUNNEL", 70),
            "auto": ("AUTO", 60),
        }
        for name, (label, width) in instance_headings.items():
            self.instance_tree.heading(name, text=label, anchor="w")
            self.instance_tree.column(name, width=width, minwidth=50, anchor="w")
        self.instance_tree.grid(row=0, column=0, sticky="ew", padx=9, pady=(9, 4))
        self.instance_xscroll = ttk.Scrollbar(
            instances_panel, orient="horizontal", command=self.instance_tree.xview
        )
        self.instance_tree.configure(xscrollcommand=self.instance_xscroll.set)
        self.instance_xscroll.grid(row=1, column=0, sticky="ew", padx=9, pady=(0, 4))
        self.instance_tree.tag_configure("ready", foreground=self.theme.ready)
        self.instance_tree.tag_configure("warning", foreground=self.theme.warning)
        self.instance_tree.tag_configure("idle", foreground=self.theme.idle)
        self._attach_row_path_tip(self.instance_tree, column=3, label=tr("menu.copy.path"))

        instance_actions = tk.Frame(instances_panel, bg=self.theme.panel)
        instance_actions.grid(row=2, column=0, sticky="ew", padx=9, pady=(0, 9))
        self.instance_start_button = self._button(
            instance_actions, "Start", self.start_selected_instance
        )
        _attach_tip(self.instance_start_button, tr("tip.instance.start"), self.theme)
        self.instance_stop_button = self._button(
            instance_actions, "Stop", self.stop_selected_instance
        )
        _attach_tip(self.instance_stop_button, tr("tip.instance.stop"), self.theme)
        self.instance_startall_button = self._button(
            instance_actions, "Start All", self.start_all_instances
        )
        _attach_tip(self.instance_startall_button, tr("tip.instance.startall"), self.theme)
        self.instance_auto_button = self._button(
            instance_actions, "Toggle Auto", self.toggle_instance_autostart
        )
        _attach_tip(self.instance_auto_button, tr("tip.instance.auto"), self.theme)
        self.instance_rescan_button = self._button(
            instance_actions, "Rescan", self.rescan_instances
        )
        _attach_tip(self.instance_rescan_button, tr("tip.instance.rescan"), self.theme)
        self.add_instance_button = self._button(
            instance_actions, tr("btn.add.connector"), self.open_add_instance_dialog
        )
        _attach_tip(
            self.add_instance_button,
            tr("tip.add.connector"),
            self.theme,
        )
        self.rename_instance_button = self._button(
            instance_actions, tr("btn.rename.connector"), self.open_rename_instance_dialog
        )
        _attach_tip(self.rename_instance_button, tr("tip.rename.connector"), self.theme)
        self.delete_instance_button = self._button(
            instance_actions, tr("btn.delete.connector"), self.delete_selected_instance
        )
        _attach_tip(
            self.delete_instance_button,
            tr("tip.delete.connector"),
            self.theme,
        )
        self.brain_button = self._button(
            instance_actions, tr("btn.brain"), self.open_brain_config
        )
        _attach_tip(
            self.brain_button,
            "Second Brain: เลือก folder สมอง (เช่น A-Wiki) 1-2 อัน\nทุก agent ที่เชื่อมเข้ามาต้องอ่านกฎเหล่านี้ก่อนทำงาน (Index เท่านั้น ประหยัด token)",
            self.theme,
        )
        self.tunnel_button = self._button(
            instance_actions, "ตั้ง Tunnel ID", self.open_tunnel_id_dialog
        )
        _attach_tip(
            self.tunnel_button,
            "วาง Tunnel ID (tunnel_...) ของตัวเชื่อมที่เลือก — สำหรับผู้ใช้ใหม่\nดูวิธีขอ ID ได้ในปุ่ม คู่มือ หมวด 'เชื่อมต่อ AI แต่ละค่าย'",
            self.theme,
        )
        self.rebind_button = self._button(
            instance_actions, "เปลี่ยนโปรเจกต์", self.open_rebind_dialog
        )
        _attach_tip(
            self.rebind_button,
            "เปลี่ยนโปรเจกต์ที่ตัวเชื่อมที่เลือกทำงานด้วย\nสำรองไฟล์เดิมเป็น .bak อัตโนมัติ · มีผลหลัง restart ตัวเชื่อม",
            self.theme,
        )
        self.upstream_button = self._button(
            instance_actions, "เช็คอัปเดท engine", self.check_upstream
        )
        _attach_tip(
            self.upstream_button,
            "ดูเวอร์ชันล่าสุดของ engine ต้นแบบ (Serena) จาก GitHub\nอ่านอย่างเดียว — ถ้ามีอัปเดท ค่อยให้ AI agent ช่วยตามทีหลัง",
            self.theme,
        )
        for index, button in enumerate(
            (
                self.instance_start_button,
                self.instance_stop_button,
                self.instance_startall_button,
                self.instance_auto_button,
                self.instance_rescan_button,
                self.brain_button,
                self.tunnel_button,
                self.rebind_button,
                self.upstream_button,
            )
        ):
            button.grid(row=index // 4, column=index % 4, padx=(0, 6), pady=(0, 3), sticky="w")
            button.state(["disabled"])
        self._set_enabled(self.upstream_button, True)  # read-only, always available

        monitor_panel = self._panel(self.root, "MONITOR")
        monitor_panel.grid(row=4, column=0, sticky="ew", padx=10, pady=(6, 0))
        monitor_panel.grid_columnconfigure(0, weight=1)
        self.monitor_text = tk.Text(
            monitor_panel,
            height=9,
            bg=self.theme.background,
            fg=self.theme.foreground,
            borderwidth=0,
            highlightthickness=0,
            wrap="none",
            state="disabled",
            font=(self.theme.monospace_font, self.theme.base_font_size),
        )
        self.monitor_text.grid(row=0, column=0, sticky="ew", padx=(9, 0), pady=(9, 4))
        self.instance_tree.bind(
            "<<TreeviewSelect>>", lambda _event: self._refresh_monitor_async(), add="+"
        )
        self._update_monitor_now()

        # Status bar (bottom, full-width) — brand watermark + update button
        status_bar = tk.Frame(self.root, bg=self.theme.background, height=24)
        status_bar.grid(row=6, column=0, sticky="ew", padx=0, pady=(0, 0))
        self._update_button = self._button(status_bar, "Check Update", self.check_for_updates)
        self._donate_button = self._button(status_bar, "Donate", self.open_donate_dialog)
        self._update_button.pack(side="right", padx=(4, 10), pady=2)
        _attach_tip(
            self._update_button,
            "ตรวจสอบเวอร์ชั่นใหม่จาก GitHub (กดแล้วเปิดหน้าดาวน์โหลด)\nCheck for a newer version on GitHub",
            self.theme,
        )
        self.brand_label = tk.Label(
            status_bar,
            text=f"  A·SUNDAY CONDUCTOR v{APP_VERSION} · by Human + AI 'A'",
            bg=self.theme.background,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 8),
            anchor="e",
        )
        self.brand_label.pack(side="right", padx=(0, 4))
        self.brand_label.bind(
            "<Button-1>",
            lambda _e: webbrowser.open("https://github.com/aase7en/A-Wiki-Conductor"),
        )

        activity_panel = self._panel(self.root, "ACTIVITY / LOG")
        activity_panel.grid(row=5, column=0, sticky="nsew", padx=10, pady=(6, 4))
        activity_panel.grid_rowconfigure(1, weight=1)
        activity_panel.grid_columnconfigure(0, weight=1)
        self.activity_text = tk.Text(
            activity_panel,
            height=9,
            bg=self.theme.background,
            fg=self.theme.foreground,
            insertbackground=self.theme.accent,
            borderwidth=0,
            highlightthickness=0,
            wrap="none",
            state="disabled",
            font=(self.theme.monospace_font, self.theme.base_font_size),
        )
        activity_scroll = ttk.Scrollbar(activity_panel, orient="vertical", command=self.activity_text.yview)
        self.activity_text.configure(yscrollcommand=activity_scroll.set)
        self.activity_text.grid(row=1, column=0, sticky="nsew", padx=(9, 0), pady=(0, 9))
        activity_scroll.grid(row=1, column=1, sticky="ns", padx=(0, 9), pady=(0, 9))
        self.log_activity("Control Center ready")
        self.root.after(1200, self._start_status_pulse)

    def _update_monitor_now(self) -> None:
        """Sync render (tests / no-selection hint path)."""
        from .instance_monitor import monitor_report
        from .local_instances import instance_health_state

        name = self._selected_instance_name()
        if name is None:
            self._render_monitor(None, None)
            return
        target = self._monitor_target(name)
        if target is None:
            self._render_monitor(name, None)
            return
        try:
            state = instance_health_state(target).value
        except Exception:
            state = "UNKNOWN"
        self._render_monitor(name, monitor_report(target.instance_root, state=state))

    def _render_monitor(self, name, report) -> None:
        """Paint the MONITOR panel; report=None means unknown/none."""
        if not self.monitor_text.winfo_exists():
            return
        state = report.get("state", "-") if report else "-"
        lines: list[str] = ["MONITOR"]
        if name is None:
            lines.append(
                "  เลือกตัวเชื่อมในตาราง CONNECTORS เพื่อดูสถานะ · PID · หน่วยความจำ · log ล่าสุด"
            )
            lines.append("  (เปิด/ปิดผ่านปุ่มในแอปได้เลย — start จากแอปไม่มีหน้าต่าง CMD)")
        elif report is None:
            lines.append(f"  {name}: ไม่พบ instance")
        else:
            alias = ""
            aliases_fn = getattr(self.service, "instance_aliases", None)
            if callable(aliases_fn):
                try:
                    alias = aliases_fn().get(name, "") or ""
                except Exception:
                    alias = ""
            header = f"  {name}" + (f"  ({alias})" if alias else "")
            pid_text = str(report["pid"]) if report["pid"] else "-"
            mem_text = f"{report['memory_mb']} MB" if report["memory_mb"] else "-"
            lines.append(f"{header}   {state}   PID {pid_text}   MEM {mem_text}")
            lines.append(f"  log: {report['log_file'] or '-'}")
            errors = report["errors"]
            lines.append(f"  errors ล่าสุด: {len(errors)}")
            lines.append("  --- tail ---")
            lines.extend(f"  {line}" for line in report["tail"])
        try:
            self.monitor_text.configure(state="normal")
            self.monitor_text.delete("1.0", "end")
            self.monitor_text.insert("1.0", chr(10).join(lines))
            self.monitor_text.configure(state="disabled")
        except tk.TclError:
            pass

    def _monitor_tick(self) -> None:
        """Auto-refresh the MONITOR panel every 5s (real entrypoint only)."""
        try:
            self._refresh_monitor_async()
        except tk.TclError:
            return
        try:
            self.root.after(5000, self._monitor_tick)
        except tk.TclError:
            pass

    def _monitor_target(self, name: str):
        cached = self._monitor_instances.get(name)
        if cached is not None:
            return cached
        return next(
            (item for item in self.service.instances() if item.name == name), None
        )

    def _refresh_monitor_async(self) -> None:
        """Fetch the monitor report off the UI thread, then render."""
        from .instance_monitor import monitor_report
        from .local_instances import instance_health_state

        name = self._selected_instance_name()
        if name is None:
            self._update_monitor_now()
            return
        target = self._monitor_target(name)
        if target is None:
            self._update_monitor_now()
            return

        def work():
            try:
                state = instance_health_state(target).value
            except Exception:
                state = "UNKNOWN"
            return monitor_report(target.instance_root, state=state)

        try:
            future = self._background_executor.submit(work)
        except Exception:
            self._update_monitor_now()
            return
        self._poll_monitor(future, name)

    def _poll_monitor(self, future, name: str) -> None:
        if not future.done():
            self.root.after(25, self._poll_monitor, future, name)
            return
        try:
            report = future.result()
        except Exception:
            return
        self._render_monitor(name, report)

    def _panel(self, parent, title: str) -> tk.Frame:
        frame = tk.Frame(
            parent,
            bg=self.theme.panel,
            highlightthickness=1,
            highlightbackground=self.theme.border,
        )
        tk.Label(
            frame,
            text=title,
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9, "bold"),
            anchor="w",
            padx=9,
            pady=8,
        ).grid(row=0, column=0, sticky="ew")
        return frame

    def _button(self, parent, text: str, command) -> ttk.Button:
        return ttk.Button(
            parent,
            text=text,
            command=command,
            style="AConductor.TButton",
        )

    @staticmethod
    def _state_tag(state: WorkerState) -> str:
        if state is WorkerState.READY:
            return "ready"
        if state in {WorkerState.STARTING, WorkerState.BUSY, WorkerState.STOPPING}:
            return "warning"
        if state is WorkerState.ERROR:
            return "error"
        return "idle"

    def refresh(self) -> None:
        snapshot = self.service.snapshot()
        self.connection_label.configure(
            text="● ONLINE" if snapshot.online else "● OFFLINE",
            fg=self.theme.ready if snapshot.online else self.theme.error,
        )

        selected_project = self.selected_project_id()
        self.project_list.delete(0, "end")
        self._project_ids.clear()
        self._project_paths.clear()
        for project in snapshot.projects:
            self._project_ids.append(project.project_id)
            self._project_paths[project.project_id] = project.root_path
            self.project_list.insert("end", f"> {project.display_name}\n  {project.root_path}")
        if selected_project in self._project_ids:
            index = self._project_ids.index(selected_project)
            self.project_list.selection_set(index)

        selected_worker = self.selected_worker_id()
        for item in self.worker_tree.get_children():
            self.worker_tree.delete(item)
        self._worker_ids.clear()
        instances = ()
        instances_fn = getattr(self.service, "instances", None)
        if callable(instances_fn):
            try:
                instances = tuple(instances_fn())
            except Exception:
                instances = ()
        path_fn = getattr(self.service, "worker_start_path", None)
        for worker in snapshot.workers:
            project_name = worker.project_display_name or "—"
            project_path = worker.project_root_path or "—"
            connector = "-"
            if callable(path_fn):
                try:
                    kind, detail = path_fn(worker.worker_id)
                    connector = detail if kind == "connector" and detail else "-"
                except Exception:
                    connector = "-"
            else:
                connector = (
                    connector_name_for_project(instances, worker.project_root_path)
                    or "-"
                )
            item = self.worker_tree.insert(
                "",
                "end",
                values=(
                    worker.worker_id,
                    worker.state.value,
                    project_name,
                    project_path,
                    connector,
                ),
                tags=(self._state_tag(worker.state),),
            )
            self._worker_ids[item] = worker.worker_id
            if selected_worker == worker.worker_id:
                self.worker_tree.selection_set(item)
                self.worker_tree.focus(item)
        self._update_lifecycle_buttons()
        self._refresh_memory_status()

    def _refresh_memory_status(self) -> None:
        """Read-only memory-presence line for the selected project (WO-P1-057)."""
        label = getattr(self, "memory_status_label", None)
        if label is None:
            return
        project_id = self.selected_project_id()
        if project_id is None:
            label.configure(
                text="สมองโปรเจกต์: เลือกโปรเจกต์เพื่อดูสถานะ",
                fg=self.theme.muted,
            )
            return
        root_path = self._project_paths.get(project_id)
        if not root_path:
            label.configure(text="สมองโปรเจกต์: —", fg=self.theme.muted)
            return
        presence = inspect_memory_presence(root_path)
        if presence.state is MemoryPresenceState.HAS_MEMORIES:
            label.configure(
                text=f"สมองโปรเจกต์: พร้อม ({presence.total_files} ไฟล์)",
                fg=self.theme.ready,
            )
        elif presence.state is MemoryPresenceState.NO_PROJECT:
            label.configure(
                text="สมองโปรเจกต์: ไม่พบ path โปรเจกต์",
                fg=self.theme.error,
            )
        else:
            label.configure(
                text="สมองโปรเจกต์: ยังไม่มีความจำ — onboarding จะทำงานเมื่อ agent เข้าครั้งแรก · หลังจบเริ่มบทสนทนาใหม่",
                fg=self.theme.warning,
            )

    def selected_project_id(self) -> str | None:
        selected = self.project_list.curselection()
        if not selected:
            return None
        index = int(selected[0])
        return self._project_ids[index] if index < len(self._project_ids) else None

    def copy_activation_prompt(self) -> str | None:
        project_id = self.selected_project_id()
        if project_id is None:
            self._handle_error("SELECT_PROJECT")
            return None
        root_path = self._project_paths.get(project_id)
        if not root_path:
            self._handle_error("SELECT_PROJECT")
            return None
        prompt = f"{SERENA_ACTIVATION_PROMPT}\nProject path: {root_path}"
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(prompt)
            self.root.update_idletasks()
        except tk.TclError:
            self._handle_error("CLIPBOARD_COPY_FAILED")
            return None
        self.log_activity(f"Copy Activate {project_id}")
        return prompt

    def selected_worker_id(self) -> str | None:
        selected = self.worker_tree.selection()
        if not selected:
            return None
        return self._worker_ids.get(selected[0])

    def add_project(self) -> None:
        selected = self._directory_picker()
        if not selected:
            return
        try:
            self.service.register_project(Path(selected))
        except ControlCenterError as exc:
            self._handle_error(exc.code)
            return
        self.log_activity(f"Add Project  {Path(selected).name}")
        self.refresh()

    def assign_selected(self) -> None:
        project_id = self.selected_project_id()
        worker_id = self.selected_worker_id()
        if project_id is None:
            self._handle_error("SELECT_PROJECT")
            return
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return
        try:
            self.service.assign_project(worker_id, project_id, mutation_allowed=True)
        except ControlCenterError as exc:
            self._handle_error(exc.code)
            return
        self.log_activity(f"Assign       {worker_id} <- {project_id}")
        self.refresh()

    def release_selected(self) -> None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return
        try:
            self.service.release_worker(worker_id)
        except ControlCenterError as exc:
            self._handle_error(exc.code)
            return
        self.log_activity(f"Release      {worker_id}")
        self.refresh()

    def add_worker_slot(self, display_name: str | None = None) -> None:
        try:
            worker = self.service.add_worker(display_name)
        except ControlCenterError as exc:
            self._handle_error(exc.code)
            return
        self.log_activity(f"+ Worker     {worker.worker_id}  {worker.display_name}")
        self.refresh()

    def rename_selected_worker(self, new_name: str) -> None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return
        try:
            worker = self.service.rename_worker(worker_id, new_name)
        except ControlCenterError as exc:
            self._handle_error(exc.code)
            return
        self.log_activity(f"Rename       {worker_id} -> {worker.display_name}")
        self.refresh()

    def delete_selected_worker(self) -> None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return
        if not self._confirm(tr("dlg.delete.worker.message").format(worker_id=worker_id)):
            return
        try:
            removed = self.service.delete_worker(worker_id)
        except ControlCenterError as exc:
            self._handle_error(exc.code)
            return
        self.log_activity(f"- Worker     {removed.worker_id}")
        self.refresh()

    def open_setup_wizard(self) -> tk.Toplevel | None:
        """One-stop setup wizard: installs everything and creates the first connector."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{APP_NAME} — {tr('wiz.title')}")
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        dialog.geometry("560x420")

        self._wiz_step = 0
        self._wiz_frame = tk.Frame(dialog, bg=self.theme.panel, padx=20, pady=20)
        self._wiz_frame.pack(fill="both", expand=True)
        self._wiz_button_bar = tk.Frame(dialog, bg=self.theme.panel, padx=20, pady=10)
        self._wiz_button_bar.pack(fill="x")
        self._wizard_dialog = dialog
        self._render_wizard_step()
        return dialog

    def _render_wizard_step(self) -> None:
        for widget in self._wiz_frame.winfo_children():
            widget.destroy()
        for widget in self._wiz_button_bar.winfo_children():
            widget.destroy()

        step = self._wiz_step
        frame = self._wiz_frame
        theme = self.theme

        def label(text, **kwargs):
            return tk.Label(frame, text=text, bg=theme.panel, fg=theme.foreground,
                          font=(theme.monospace_font, 10), justify="left", **kwargs)

        def header(text):
            tk.Label(frame, text=text, bg=theme.panel, fg=theme.accent,
                    font=(theme.monospace_font, 11, "bold"), anchor="w").pack(
                    fill="x", pady=(0, 12))

        def button_bar(back=None, nxt=None):
            if back:
                self._button(self._wiz_button_bar, tr("wiz.back"), back).pack(side="left", padx=(0, 8))
            if nxt:
                self._button(self._wiz_button_bar, tr("wiz.next"), nxt).pack(side="right")

        if step == 0:
            header(tr("wiz.title"))
            label(tr("wiz.welcome"), wraplength=480).pack(fill="x")
            button_bar(nxt=lambda: self._wizard_advance())

        elif step == 1:
            header(tr("wiz.check"))
            from .setup_wizard import check_system
            status = check_system()
            items = [
                ("uv (package manager)", status.get("uv")),
                ("Python 3.13", status.get("python_313")),
                ("Serena engine", status.get("serena")),
                ("tunnel-client", status.get("tunnel_client")),
            ]
            for name, installed in items:
                mark = "OK " if installed else "-- "
                color = theme.ready if installed else theme.muted
                tk.Label(frame, text=f"  {mark}  {name}", bg=theme.panel, fg=color,
                        font=(theme.monospace_font, 10), anchor="w").pack(fill="x", pady=2)
            missing = [n for n, ok in items if not ok]
            if missing:
                label(f"\n{len(missing)} รายการต้องติดตั้ง — กด Next เพื่อดำเนินการ\n{len(missing)} items need installing — press Next").pack(fill="x", pady=(12, 0))
            else:
                label("\nทุกอย่างพร้อมแล้ว! กด Next เพื่อสร้าง Connector\nEverything ready! Press Next to create a connector").pack(fill="x", pady=(12, 0))
            button_bar(
                back=lambda: self._wizard_back(),
                nxt=lambda: self._wizard_advance(),
            )

        elif step == 2:
            header(tr("wiz.install"))
            self._wiz_log = tk.Text(frame, height=12, bg=theme.background, fg=theme.foreground,
                                  font=(theme.monospace_font, 9), state="disabled", wrap="word")
            self._wiz_log.pack(fill="both", expand=True)
            self._button(self._wiz_button_bar, tr("wiz.install"), self._wizard_run_installs).pack(side="right")
            button_bar(back=lambda: self._wizard_back())

        elif step == 3:
            header(tr("wiz.instance"))
            label("ชื่อ Connector (English):").pack(anchor="w", pady=(0, 4))
            self._wiz_name = ttk.Entry(frame, font=(theme.monospace_font, 10), width=30)
            self._wiz_name.insert(0, "sunday-worker-1")
            self._wiz_name.pack(fill="x", pady=(0, 8))
            label("พาธโปรเจกต์ (เช่น A:\\GitHub\\my-project):").pack(anchor="w", pady=(0, 4))
            self._wiz_project = ttk.Entry(frame, font=(theme.monospace_font, 10), width=50)
            self._wiz_project.pack(fill="x", pady=(0, 12))

            label("เลือก Backend:").pack(anchor="w", pady=(0, 4))
            self._wiz_backend = tk.StringVar(value="serena")
            tk.Radiobutton(frame, text="Filesystem (ง่าย — อ่าน/เขียนไฟล์ ผ่าน Node.js)",
                variable=self._wiz_backend, value="filesystem",
                bg=theme.panel, fg=theme.foreground, selectcolor=theme.background,
                font=(theme.monospace_font, 9), anchor="w").pack(anchor="w", pady=2)
            tk.Radiobutton(frame, text="Serena (เต็มรูปแบบ — วิเคราะห์โค้ด ต้องติดตั้ง Python)",
                variable=self._wiz_backend, value="serena",
                bg=theme.panel, fg=theme.foreground, selectcolor=theme.background,
                font=(theme.monospace_font, 9), anchor="w").pack(anchor="w", pady=2)
            tk.Radiobutton(frame, text="Google Stitch (design/prototyping — ต้องมี Stitch MCP)",
                variable=self._wiz_backend, value="stitch",
                bg=theme.panel, fg=theme.foreground, selectcolor=theme.background,
                font=(theme.monospace_font, 9), anchor="w").pack(anchor="w", pady=2)

            # Stitch-specific fields (visible only when stitch is selected)
            self._wiz_stitch_frame = tk.Frame(frame, bg=theme.panel)
            label("Stitch MCP folder (ที่มี artifact-keyserver.mjs):").pack(
                in_=self._wiz_stitch_frame, anchor="w", pady=(8, 2))
            self._wiz_stitch_path = ttk.Entry(
                self._wiz_stitch_frame, font=(theme.monospace_font, 10), width=50)
            self._wiz_stitch_path.insert(0, "C:\AI\stitch-mcp")
            self._wiz_stitch_path.pack(in_=self._wiz_stitch_frame, fill="x", pady=(0, 4))
            label("Stitch API Key (บันทึกเป็น sti-key.txt):").pack(
                in_=self._wiz_stitch_frame, anchor="w", pady=(0, 2))
            self._wiz_stitch_key = ttk.Entry(
                self._wiz_stitch_frame, font=(theme.monospace_font, 10), width=50, show="*")
            self._wiz_stitch_key.pack(in_=self._wiz_stitch_frame, fill="x")

            def toggle_stitch_fields(*_args):
                if self._wiz_backend.get() == "stitch":
                    self._wiz_stitch_frame.pack(fill="x", pady=(4, 0))
                else:
                    self._wiz_stitch_frame.pack_forget()

            self._wiz_backend.trace_add("write", toggle_stitch_fields)
            toggle_stitch_fields()

            button_bar(back=lambda: self._wizard_back(), nxt=lambda: self._wizard_create_instance())

        elif step == 4:
            header(tr("wiz.credentials"))
            link = tk.Label(frame, text="1. สร้าง Tunnel ID ที่ OpenAI Platform → คลิกที่นี่",
                          bg=theme.panel, fg=theme.accent, font=(theme.monospace_font, 9, "underline"),
                          cursor="hand2")
            link.pack(anchor="w", pady=(0, 4))
            link.bind("<Button-1>", lambda e: webbrowser.open(
                "https://platform.openai.com/settings/organization/tunnels"))
            label("Tunnel ID (tunnel_xxx...):").pack(anchor="w", pady=(0, 4))
            self._wiz_tunnel = ttk.Entry(frame, font=(theme.monospace_font, 10), width=50)
            self._wiz_tunnel.pack(fill="x", pady=(0, 8))
            label("2. Runtime API Key (sk-...):").pack(anchor="w", pady=(0, 4))
            self._wiz_apikey = ttk.Entry(frame, font=(theme.monospace_font, 10), width=50, show="*")
            self._wiz_apikey.pack(fill="x", pady=(0, 8))
            button_bar(back=lambda: self._wizard_back(), nxt=lambda: self._wizard_save_credentials())

        elif step == 5:
            header(tr("wiz.finish"))
            label("Setup เสร็จสมบูรณ์!\nSetup complete!\n\nกดปุ่ม Start ในหน้าหลักเพื่อเริ่มใช้งาน\nPress Start on the main window to begin.").pack(fill="x")
            self._button(self._wiz_button_bar, tr("btn.close"), lambda: self._wizard_dialog.destroy()).pack(side="right")

    def _wizard_advance(self) -> None:
        self._wiz_step = min(self._wiz_step + 1, 5)
        self._render_wizard_step()

    def _wizard_back(self) -> None:
        self._wiz_step = max(self._wiz_step - 1, 0)
        self._render_wizard_step()

    def _wizard_log_write(self, text: str) -> None:
        log = getattr(self, "_wiz_log", None)
        if log is not None and log.winfo_exists():
            log.configure(state="normal")
            log.insert("end", text + "\n")
            log.see("end")
            log.configure(state="disabled")
            self.root.update_idletasks()

    def _wizard_run_installs(self) -> None:
        from .setup_wizard import Installer

        installer = Installer()
        try:
            self._wizard_log_write("Installing uv...")
            installer.install_uv()
            self._wizard_log_write("  OK")
        except Exception as exc:
            self._wizard_log_write(f"  SKIP: {exc}")

        try:
            self._wizard_log_write("Installing Python 3.13...")
            installer.install_python()
            self._wizard_log_write("  OK")
        except Exception as exc:
            self._wizard_log_write(f"  SKIP: {exc}")

        try:
            self._wizard_log_write("Installing Serena...")
            installer.install_serena()
            self._wizard_log_write("  OK")
        except Exception as exc:
            self._wizard_log_write(f"  SKIP: {exc}")

        try:
            self._wizard_log_write("Installing tunnel-client...")
            installer.install_tunnel_client()
            self._wizard_log_write("  OK")
        except Exception as exc:
            self._wizard_log_write(f"  SKIP: {exc}")

        try:
            self._wizard_log_write("Installing Node.js...")
            installer.install_nodejs()
            self._wizard_log_write("  OK")
        except Exception as exc:
            self._wizard_log_write(f"  SKIP: {exc}")

        self._wizard_log_write("\nDone! Press Next to create your first connector.")
        self._button(self._wiz_button_bar, tr("wiz.next"), lambda: self._wizard_advance()).pack(side="right")

    def _wizard_create_instance(self) -> None:
        from .setup_wizard import FirstInstanceCreator, SetupWizardError

        name = self._wiz_name.get().strip() or "sunday-worker-1"
        project = self._wiz_project.get().strip()

        if not project:
            self._handle_error("PROJECT_NOT_FOUND")
            return

        from .platform_support import default_instances_root
        creator = FirstInstanceCreator(instances_root=default_instances_root())
        try:
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            base = Path(local_app_data) if local_app_data else Path.home()
            tc_dir = base / "Programs" / "A-Conductor" / "dwb-serena-tunnel-starter" / "tunnel-client"
            creator.create(
                name=name,
                project_path=project,
                tunnel_client_path=tc_dir / "tunnel-client.exe",
                api_key_file=tc_dir / "config" / "api-key.dpapi",
                backend=getattr(self, "_wiz_backend", None) and self._wiz_backend.get() or "serena",
                stitch_mcp_path=getattr(self, "_wiz_stitch_path", None) and self._wiz_stitch_path.get() or "",
                stitch_api_key=getattr(self, "_wiz_stitch_key", None) and self._wiz_stitch_key.get() or "",
            )
            self.log_activity(f"Wizard       created {name}")
            self._wizard_advance()
        except SetupWizardError as exc:
            self._handle_error(getattr(exc, "code", "INSTANCE_CREATE_FAILED"))
        except Exception as exc:
            self._handle_error("INSTANCE_CREATE_FAILED")

    def _wizard_save_credentials(self) -> None:
        import base64
        import ctypes
        import ctypes.wintypes

        tunnel_id = self._wiz_tunnel.get().strip()
        api_key = self._wiz_apikey.get().strip()

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        base = Path(local_app_data) if local_app_data else Path.home()
        tc_config = base / "Programs" / "A-Conductor" / "dwb-serena-tunnel-starter" / "config"
        tc_config.mkdir(parents=True, exist_ok=True)

        if tunnel_id:
            (tc_config / "tunnel-id.txt").write_text(tunnel_id + "\n", encoding="utf-8")

        if api_key:
            try:
                encrypted = ctypes.windll.crypt32.CryptProtectData(
                    ctypes.create_string_buffer(api_key.encode()),
                    None, None, None, None, 0, None
                )
                (tc_config / "api-key.dpapi").write_bytes(api_key.encode())
            except Exception:
                (tc_config / "api-key.dpapi").write_text(api_key, encoding="utf-8")

        self.log_activity("Wizard       credentials saved")
        self._wizard_advance()

    def open_donate_dialog(self) -> tk.Toplevel | None:
        """Support dialog: GitHub Sponsors + PromptPay QR + TrueWallet."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{APP_NAME} — Support / สนับสนุน")
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)

        frame = tk.Frame(dialog, bg=self.theme.panel, padx=20, pady=20)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="💝 สนับสนุนการพัฒนา / Support This Project",
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 12, "bold"),
        ).pack(pady=(0, 12))

        # GitHub Sponsors button
        sponsor_label = tk.Label(
            frame,
            text="⭐ GitHub Sponsors (International)",
            bg=self.theme.panel,
            fg=self.theme.ready,
            font=(self.theme.monospace_font, 10, "underline"),
            cursor="hand2",
        )
        sponsor_label.pack(pady=(0, 4))
        sponsor_label.bind(
            "<Button-1>",
            lambda _e: webbrowser.open("https://github.com/sponsors/aase7en"),
        )
        tk.Label(
            frame,
            text="github.com/sponsors/aase7en",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 8),
        ).pack(pady=(0, 12))

        # PromptPay QR (if image exists)
        qr_path = self._find_donate_qr()
        if qr_path is not None:
            tk.Label(
                frame,
                text="📱 PromptPay / TrueWallet",
                bg=self.theme.panel,
                fg=self.theme.foreground,
                font=(self.theme.monospace_font, 10, "bold"),
            ).pack(pady=(4, 4))
            try:
                photo = tk.PhotoImage(file=str(qr_path))
                # Scale down if too large
                if photo.width() > 240:
                    ratio = 240 / photo.width()
                    photo = photo.subsample(int(1 / ratio), int(1 / ratio))
                qr_label = tk.Label(frame, image=photo, bg=self.theme.panel)
                qr_label.image = photo  # keep reference
                qr_label.pack(pady=(0, 8))
            except tk.TclError:
                pass  # image format not supported, skip
        else:
            tk.Label(
                frame,
                text="📱 PromptPay / TrueWallet\n\nเพิ่ม QR Code ได้ที่:\nassets/donate-promptpay-qr.png\n\n(Generate QR from your bank app,\nsave as PNG, place in assets/ folder)",
                bg=self.theme.panel,
                fg=self.theme.muted,
                font=(self.theme.monospace_font, 9),
                justify="center",
            ).pack(pady=(4, 12))

        tk.Label(
            frame,
            text="ทุกจำนวนช่วยให้โปรเจกต์พัฒนาต่อได้ ขอบคุณครับ 🙏\nEvery amount helps keep this project going. Thank you!",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 8),
            justify="center",
        ).pack(pady=(8, 0))

        self._button(frame, "Close", lambda: dialog.destroy()).pack(pady=(12, 0))
        return dialog

    def _find_donate_qr(self) -> Path | None:
        """Locate the donate QR code image (dev layout or frozen bundle)."""
        import sys as _sys

        candidates = []
        bundle = getattr(_sys, "_MEIPASS", None)
        if bundle:
            candidates.append(Path(bundle) / "assets" / "donate-promptpay-qr.png")
        candidates.append(Path(__file__).resolve().parents[2] / "assets" / "donate-promptpay-qr.png")
        for candidate in candidates:
            if candidate.is_file():
                return candidate
        return None

    def check_for_updates(self) -> None:
        """Check GitHub Releases for a newer version; show result; open browser if newer."""
        from .update_checker import check_for_update

        self.log_activity("Update check  ...")
        try:
            result = check_for_update(APP_VERSION)
        except Exception:
            self._handle_error("UPSTREAM_CHECK_FAILED")
            return
        if result.error:
            self._handle_error("UPSTREAM_CHECK_FAILED")
            return
        if result.is_newer and result.download_url:
            self.log_activity(
                f"Update        v{APP_VERSION} -> v{result.latest_version} available"
            )
            if self._confirm(
                "มีเวอร์ชั่นใหม่ v"
                + str(result.latest_version)
                + " (ปัจจุบัน v"
                + APP_VERSION
                + ")\n\nกด ยืนยัน เพื่อเปิดหน้าดาวน์โหลด\n(A new version is available — open the download page?)"
            ):
                webbrowser.open(result.download_url)
        else:
            self.log_activity(f"Update        up to date (v{APP_VERSION})")
            self._confirm(
                "ใช้เวอร์ชั่นล่าสุดแล้ว (v" + APP_VERSION + ")\nYou are up to date."
            )

    def _on_close_request(self) -> None:
        """Window close: optionally stop every connector, reap wrappers, exit."""
        if getattr(self, "_closing", False):
            return
        self._closing = True
        stop_all = True
        getter = getattr(self.service, "get_preference", None)
        if callable(getter):
            try:
                pref = getter("shutdown_stops_instances")
                stop_all = True if pref is None else bool(pref)
            except Exception:
                stop_all = True
        stopped: list[tuple[str, bool]] = []
        if stop_all:
            try:
                self.log_activity("Closing       stopping all connectors ...")
                stopped = self.service.stop_all_instances()
                for name, ok in stopped:
                    self.log_activity(f"Close-stop    {name} {'OK' if ok else 'FAILED'}")
            except Exception:
                stopped = []
        if stopped:
            # Only shell out to the reaper when something was actually running.
            try:
                from .instance_runtime import reap_instance_wrappers

                for instance in self.service.instances():
                    reap_instance_wrappers(instance.instance_root)
            except Exception:
                pass
        self.root.destroy()

    def _tree_row_path(self, tree, item, *, column: int) -> str | None:
        try:
            values = tree.item(item, "values")
        except tk.TclError:
            return None
        if not values or len(values) <= column:
            return None
        return str(values[column]) or None

    def _copy_path_to_clipboard(self, path: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(path)
        self.log_activity(f"Copy path    {path}")

    def _attach_row_path_tip(self, tree, *, column: int, label: str) -> None:
        def provider(item) -> str | None:
            return self._tree_row_path(tree, item, column=column)

        self._row_path_tip_providers[tree] = provider
        RowPathTip(tree, provider, self.theme)

        def on_context(event) -> None:
            row = tree.identify_row(event.y)
            if not row:
                return
            tree.selection_clear()
            tree.selection_set(row)
            path = provider(row)
            if not path:
                return
            menu = tk.Menu(tree, tearoff=0, bg=self.theme.panel, fg=self.theme.muted)
            menu.add_command(
                label=label, command=lambda bound=path: self._copy_path_to_clipboard(bound)
            )
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        tree.bind("<Button-3>", on_context, add="+")

    def _confirm(self, message: str) -> bool:
        answer = {"ok": False}
        dialog = tk.Toplevel(self.root)
        dialog.title(f'{APP_NAME} — {tr("dlg.confirm.title")}')
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(False, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text=message,
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 10),
            wraplength=340,
            justify="left",
        ).pack(pady=(0, 10))
        buttons = tk.Frame(frame, bg=self.theme.panel)
        buttons.pack(fill="x")

        def close(ok: bool) -> None:
            answer["ok"] = ok
            dialog.destroy()

        self._button(buttons, tr("dlg.confirm.ok"), lambda: close(True)).pack(side="right", padx=(6, 0))
        self._button(buttons, tr("dlg.confirm.cancel"), lambda: close(False)).pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", lambda: close(False))
        dialog.grab_set()
        dialog.wait_window()
        return answer["ok"]

    def open_add_worker_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title(f'{APP_NAME} — {tr("dlg.add.worker.title")}')
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(1, weight=1)
        tk.Label(
            frame,
            text="> " + tr("dlg.add.worker.header"),
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        tk.Label(
            frame,
            text=tr("dlg.add.worker.name"),
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        ).grid(row=1, column=0, columnspan=2, sticky="w")
        name_entry = ttk.Entry(frame, font=(self.theme.monospace_font, 10))
        name_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 10))

        def submit() -> None:
            dialog.destroy()
            self.add_worker_slot(name_entry.get().strip() or None)

        name_entry.bind("<Return>", lambda _event: submit())
        self._button(frame, tr("dlg.add.worker.submit"), submit).grid(row=3, column=1, sticky="e")
        name_entry.focus_set()

    def open_rename_worker_dialog(self) -> None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return
        row = self._selected_worker_row()
        current = row.display_name if row is not None else worker_id
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{APP_NAME} — แก้ชื่อ Worker — {worker_id}")
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(1, weight=1)
        tk.Label(
            frame,
            text=f"> แก้ชื่อ  {worker_id}",
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        tk.Label(
            frame,
            text=tr("dlg.rename.worker.name"),
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        ).grid(row=1, column=0, columnspan=2, sticky="w")
        name_entry = ttk.Entry(frame, font=(self.theme.monospace_font, 10))
        name_entry.insert(0, current)
        name_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 10))

        def submit() -> None:
            new_name = name_entry.get().strip()
            if not new_name:
                self._handle_error("WORKER_NAME_INVALID")
                return
            dialog.destroy()
            self.rename_selected_worker(new_name)

        name_entry.bind("<Return>", lambda _event: submit())
        self._button(frame, tr("dlg.rename.worker.submit"), submit).grid(row=3, column=1, sticky="e")
        name_entry.focus_set()

    @staticmethod
    def _set_enabled(button: ttk.Button, enabled: bool) -> None:
        button.state(["!disabled"] if enabled else ["disabled"])

    def _selected_worker_row(self):
        worker_id = self.selected_worker_id()
        if worker_id is None:
            return None
        return next(
            (row for row in self.service.snapshot().workers if row.worker_id == worker_id),
            None,
        )

    def _has_lifecycle_service(self) -> bool:
        return all(
            callable(getattr(self.service, name, None))
            for name in ("start_worker", "stop_worker", "restart_worker")
        )

    def _has_setup_service(self) -> bool:
        return all(
            callable(getattr(self.service, name, None))
            for name in ("worker_setup", "save_worker_setup")
        )

    def _has_settings_service(self) -> bool:
        return all(
            callable(getattr(self.service, name, None))
            for name in ("worker_settings", "save_worker_settings")
        )

    def _readiness(self, worker_id: str) -> SetupReadiness:
        fn = getattr(self.service, "lifecycle_readiness", None)
        if not callable(fn):
            return SetupReadiness(True, "READY")
        try:
            result = fn(worker_id)
        except RuntimeSetupError as exc:
            return SetupReadiness(False, exc.code)
        except Exception:
            return SetupReadiness(False, "SETUP_READINESS_FAILED")
        return result if isinstance(result, SetupReadiness) else SetupReadiness(False, "SETUP_READINESS_INVALID")

    def _update_lifecycle_buttons(self) -> None:
        row = self._selected_worker_row()
        has_lifecycle = self._has_lifecycle_service()
        has_setup = self._has_setup_service()
        self._set_enabled(self.setup_button, row is not None and has_setup)
        self._set_enabled(
            self.config_button, row is not None and self._has_settings_service()
        )
        if row is None or row.assignment_id is None:
            self._set_enabled(self.start_button, False)
            self._set_enabled(self.stop_button, False)
            self._set_enabled(self.restart_button, False)
            return
        if not has_lifecycle and self._worker_start_kind(row.worker_id) != "connector":
            self._set_enabled(self.start_button, False)
            self._set_enabled(self.stop_button, False)
            self._set_enabled(self.restart_button, False)
            return

        kind = self._worker_start_kind(row.worker_id)
        startable = kind != "blocked"
        ready = self._readiness(row.worker_id).ready if has_lifecycle else False
        connector_mode = kind == "connector"
        self._set_enabled(
            self.start_button,
            startable and (connector_mode or row.state is WorkerState.STOPPED),
        )
        self._set_enabled(
            self.stop_button,
            row.state in {WorkerState.READY, WorkerState.BUSY, WorkerState.STARTING},
        )
        self._set_enabled(
            self.restart_button,
            row.state is WorkerState.READY and startable,
        )

    def _worker_start_kind(self, worker_id: str) -> str:
        """'connector' | 'lifecycle' | 'blocked' — how Start would run."""
        path_fn = getattr(self.service, "worker_start_path", None)
        if callable(path_fn):
            try:
                kind, _detail = path_fn(worker_id)
                return kind
            except Exception:
                return "blocked"
        instances_fn = getattr(self.service, "instances", None)
        if callable(instances_fn):
            row = self._selected_worker_row()
            root = row.project_root_path if row is not None else None
            try:
                if connector_name_for_project(tuple(instances_fn()), root):
                    return "connector"
            except Exception:
                pass
        return "lifecycle" if self._readiness(worker_id).ready else "blocked"

    def _submit_lifecycle(self, action: str, worker_id: str, command) -> None:
        self.log_activity(f"{action:<12} {worker_id} QUEUED")
        self._set_enabled(self.start_button, False)
        self._set_enabled(self.stop_button, False)
        self._set_enabled(self.restart_button, False)
        future = self._background_executor.submit(command, worker_id)
        self.root.after(0, self._poll_lifecycle_future, action, worker_id, future)

    def _poll_lifecycle_future(
        self,
        action: str,
        worker_id: str,
        future: Future,
    ) -> None:
        if not future.done():
            self.root.after(25, self._poll_lifecycle_future, action, worker_id, future)
            return
        try:
            result = future.result()
        except LifecycleCoordinatorError as exc:
            self._handle_error(exc.code)
            self._update_lifecycle_buttons()
            return
        except Exception:
            self._handle_error("LIFECYCLE_COMMAND_FAILED")
            self._update_lifecycle_buttons()
            return

        if not isinstance(result, LifecycleExecutionResult):
            self._handle_error("LIFECYCLE_RESULT_INVALID")
            self._update_lifecycle_buttons()
            return
        self.log_activity(
            f"{action:<12} {worker_id} {result.state.value} {result.reason_code}"
        )
        self.refresh()

    def _run_selected_lifecycle(self, action: str, method_name: str) -> None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return
        command = getattr(self.service, method_name, None)
        if not callable(command):
            self._handle_error("LIFECYCLE_NOT_WIRED")
            return
        self._submit_lifecycle(action, worker_id, command)

    def start_selected(self) -> None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return
        if self._worker_start_kind(worker_id) == "connector":
            path_fn = getattr(self.service, "worker_start_path", None)
            name = None
            if callable(path_fn):
                try:
                    _kind, name = path_fn(worker_id)
                except Exception:
                    name = None
            if name:
                self._submit_instance_action("START-W", name)
                return
            self._handle_error("CONNECTOR_MATCH_MISSING")
            return
        self._run_selected_lifecycle("START", "start_worker")

    def stop_selected(self) -> None:
        self._run_selected_lifecycle("STOP", "stop_worker")

    def restart_selected(self) -> None:
        self._run_selected_lifecycle("RESTART", "restart_worker")

    def open_runtime_setup(self) -> tk.Toplevel | None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return None
        worker_setup = getattr(self.service, "worker_setup", None)
        if not callable(worker_setup):
            self._handle_error("RUNTIME_SETUP_NOT_AVAILABLE")
            return None
        try:
            draft = worker_setup(worker_id)
        except RuntimeSetupError as exc:
            self._handle_error(exc.code)
            return None
        except Exception:
            self._handle_error("RUNTIME_SETUP_FAILED")
            return None
        if not isinstance(draft, WorkerSetupDraft):
            self._handle_error("RUNTIME_SETUP_RESULT_INVALID")
            return None

        self._setup_draft = draft
        dialog = tk.Toplevel(self.root)
        dialog.title(f"{APP_NAME} — Runtime Setup — {worker_id}")
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text=f"> RUNTIME SETUP  {worker_id}  {'CONFIGURED' if draft.configured else 'UNCONFIGURED'}",
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        fields = (
            ("instance_root", "Instance root", draft.instance_root),
            ("serena_home", "SERENA_HOME", draft.serena_home),
            ("run_dir", "Run directory", draft.run_dir),
            ("log_dir", "Log directory", draft.log_dir),
            ("health_host", "Health host", draft.health_host),
            ("health_port", "Health port", str(draft.health_port)),
            ("runtime_executable", "Runtime executable", draft.runtime_executable_ref),
            ("profile_template", "Profile template", draft.profile_template_ref),
            ("tunnel_reference_id", "Tunnel ref ID", draft.tunnel_binding_ref or ""),
            ("tunnel_reference_file", "Tunnel ref file", draft.reference_file_path or ""),
            ("tunnel_reference_root", "Tunnel ref allowed root", draft.reference_allowed_root or ""),
            ("serena_config_source", "Serena config source", ""),
        )
        self._setup_entries = {}
        for row_index, (key, label, value) in enumerate(fields, start=1):
            tk.Label(
                frame,
                text=label,
                bg=self.theme.panel,
                fg=self.theme.muted,
                font=(self.theme.monospace_font, 9),
                anchor="w",
            ).grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=2)
            entry = ttk.Entry(frame, width=72)
            entry.insert(0, value)
            entry.grid(row=row_index, column=1, columnspan=2, sticky="ew", pady=2)
            self._setup_entries[key] = entry

        button_row = len(fields) + 1
        self._button(frame, "Save", lambda: self.save_runtime_setup(dialog)).grid(
            row=button_row, column=0, sticky="w", pady=(12, 0)
        )
        self._button(frame, "Capture Exact Git", self.capture_exact_identity).grid(
            row=button_row, column=1, sticky="w", pady=(12, 0)
        )
        self._button(frame, "No Git", self.save_no_git_identity).grid(
            row=button_row, column=2, sticky="w", pady=(12, 0)
        )
        return dialog

    def save_runtime_setup(self, dialog: tk.Toplevel | None = None) -> None:
        draft = self._setup_draft
        save = getattr(self.service, "save_worker_setup", None)
        if draft is None or not callable(save):
            self._handle_error("RUNTIME_SETUP_NOT_AVAILABLE")
            return
        try:
            health_port = int(self._setup_entries["health_port"].get().strip())
        except (KeyError, ValueError):
            self._handle_error("HEALTH_PORT_INVALID")
            return

        def value(key: str) -> str:
            return self._setup_entries[key].get().strip()

        updated = WorkerSetupDraft(
            worker_id=draft.worker_id,
            configured=draft.configured,
            instance_root=value("instance_root"),
            serena_home=value("serena_home"),
            run_dir=value("run_dir"),
            log_dir=value("log_dir"),
            health_host=value("health_host"),
            health_port=health_port,
            runtime_executable_ref=value("runtime_executable"),
            profile_template_ref=value("profile_template"),
            tunnel_binding_ref=value("tunnel_reference_id") or None,
            reference_file_path=value("tunnel_reference_file") or None,
            reference_allowed_root=value("tunnel_reference_root") or None,
            startup_timeout_seconds=draft.startup_timeout_seconds,
            stop_timeout_seconds=draft.stop_timeout_seconds,
        )
        source = value("serena_config_source") or None
        try:
            saved = save(updated, serena_config_source=source)
        except RuntimeSetupError as exc:
            self._handle_error(exc.code)
            return
        except Exception:
            self._handle_error("RUNTIME_SETUP_SAVE_FAILED")
            return
        if not isinstance(saved, WorkerSetupDraft):
            self._handle_error("RUNTIME_SETUP_RESULT_INVALID")
            return
        self._setup_draft = saved
        self.log_activity(f"Setup        {saved.worker_id} SAVED")
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()
        self.refresh()

    def capture_exact_identity(self) -> None:
        self._run_identity_action("EXACT", "capture_exact_project_identity")

    def save_no_git_identity(self) -> None:
        self._run_identity_action("NO_GIT", "save_no_git_project_identity")

    def _run_identity_action(self, label: str, method_name: str) -> None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return
        command = getattr(self.service, method_name, None)
        if not callable(command):
            self._handle_error("RUNTIME_SETUP_NOT_AVAILABLE")
            return
        try:
            command(worker_id)
        except RuntimeSetupError as exc:
            self._handle_error(exc.code)
            return
        except Exception:
            self._handle_error("PROJECT_IDENTITY_SAVE_FAILED")
            return
        self.log_activity(f"Identity     {worker_id} {label}")
        self._update_lifecycle_buttons()

    def _handle_error(self, code: str) -> None:
        self.log_activity(f"ERROR        {code}")
        self._error_handler(code)

    def _show_error(self, code: str) -> tk.Toplevel | None:
        """Themed, teaching error popup (minimal CLI look)."""
        table = ERROR_EXPLANATIONS_EN if get_language() == "en" else ERROR_EXPLANATIONS
        title, detail_parts = table.get(code, table["GENERIC"])
        detail = chr(10).join(detail_parts)
        window = tk.Toplevel(self.root)
        window.title(APP_NAME + " — " + tr("win.error"))
        window.configure(bg=self.theme.panel)
        window.transient(self.root)
        window.resizable(True, False)
        frame = tk.Frame(window, bg=self.theme.panel, padx=16, pady=14)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text=f"! {title}",
            bg=self.theme.panel,
            fg=self.theme.error,
            font=(self.theme.monospace_font, 11, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        tk.Label(
            frame,
            text=code,
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))
        tk.Label(
            frame,
            text=detail,
            bg=self.theme.panel,
            fg=self.theme.foreground,
            font=(self.theme.monospace_font, 9),
            justify="left",
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(0, 10))
        tk.Label(
            frame,
            text=tr("err.footer"),
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 8),
            anchor="w",
        ).grid(row=3, column=0, sticky="w", pady=(0, 4))
        self._button(
            frame, "ปิด", lambda: window.destroy() if window.winfo_exists() else None
        ).grid(row=4, column=0, sticky="w")
        return window

    def _start_status_pulse(self) -> None:
        """Slow, gentle pulse for the ONLINE dot (minimal theme, ~1.2s cycle)."""
        self._pulse_on = not getattr(self, "_pulse_on", False)
        text = str(self.connection_label.cget("text"))
        if "ONLINE" in text:
            color = self.theme.ready if self._pulse_on else self.theme.ready_dim
            try:
                self.connection_label.configure(fg=color)
            except tk.TclError:
                return
        if self.root.winfo_exists():
            self.root.after(1200, self._start_status_pulse)

    def log_activity(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.activity_text.configure(state="normal")
        self.activity_text.insert("end", f"{stamp}  {text}\n")
        self.activity_text.see("end")
        self.activity_text.configure(state="disabled")

    def _on_palette_shortcut(self, _event=None):
        return None

    def _open_guide_link(self, widget, index: str) -> None:
        for tag in widget.tag_names(index):
            if tag == "link":
                start = widget.tag_prevrange("link", index + "+1c")
                if start:
                    url = widget.get(start[0], start[1])
                    webbrowser.open(url)
                    return

    def open_preferences(self) -> tk.Toplevel | None:
        """Global preferences dialog — CLI-styled switches with explanations."""
        getter = getattr(self.service, "get_preference", None)
        setter = getattr(self.service, "set_preference", None)
        if not callable(getter) or not callable(setter):
            self._handle_error("PREFERENCES_NOT_AVAILABLE")
            return None

        window = tk.Toplevel(self.root)
        window.title(APP_NAME + " — " + tr("win.settings"))
        window.configure(bg=self.theme.panel)
        window.transient(self.root)
        window.resizable(True, False)
        frame = tk.Frame(window, bg=self.theme.panel, padx=16, pady=14)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)
        tk.Label(
            frame,
            text="> การตั้งค่ารวม  (เปลี่ยนแล้วมีผลทันที)",
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        try:
            supervised = getter("supervised")
        except Exception:
            self._handle_error("PREFERENCES_LOAD_FAILED")
            return None
        if supervised is None:
            supervised = True

        supervised_var = tk.BooleanVar(value=supervised)

        checkbox = tk.Checkbutton(
            frame,
            text="โหมด Supervised  (คุมงานเบื้องหลัง: บันทึกทุกคำสั่ง · กันสั่งซ้ำ · เก็บผลแม้ timeout)",
            variable=supervised_var,
            bg=self.theme.panel,
            fg=self.theme.foreground,
            selectcolor=self.theme.background,
            activebackground=self.theme.panel,
            activeforeground=self.theme.foreground,
            highlightthickness=0,
            font=(self.theme.monospace_font, 9),
            anchor="w",
            justify="left",
            wraplength=460,
            command=lambda: self._save_supervised_preference(setter, supervised_var),
        )
        checkbox.grid(row=2, column=0, sticky="w")
        _attach_tip(
            checkbox,
            "ON = ทุกคำสั่ง native (git/pytest/compileall) ถูกคุมตั้งแต่เกิดจนจบ:\nบันทึกลงฐานข้อมูล + กันงานซ้ำ + เก็บ output ครบ\nOFF = รันเร็วขึ้นเล็กน้อย แต่ไม่มีการบันทึก/กันซ้ำ\n(แนะนำ: ON)",
            self.theme,
        )
        tk.Label(
            frame,
            text="ON: ปลอดภัยกว่า บันทึกทุกงาน กันสั่งซ้ำอัตโนมัติ · OFF: เร็วกว่า เหมาะกับงานสั้นๆ ไม่สำคัญ",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 8),
            anchor="w",
            wraplength=460,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(2, 8))

        language_var = tk.BooleanVar(value=(get_language() == "en"))

        try:
            shutdown_pref = getter("shutdown_stops_instances")
        except Exception:
            shutdown_pref = None
        shutdown_var = tk.BooleanVar(value=True if shutdown_pref is None else bool(shutdown_pref))
        shutdown_box = tk.Checkbutton(
            frame,
            text=tr("prefs.shutdown"),
            variable=shutdown_var,
            bg=self.theme.panel,
            fg=self.theme.foreground,
            selectcolor=self.theme.background,
            activebackground=self.theme.panel,
            activeforeground=self.theme.foreground,
            highlightthickness=0,
            font=(self.theme.monospace_font, 9),
            anchor="w",
            justify="left",
            wraplength=460,
            command=lambda: self._save_shutdown_preference(setter, shutdown_var),
        )
        shutdown_box.grid(row=1, column=0, sticky="w", pady=(0, 2))
        _attach_tip(shutdown_box, tr("prefs.shutdown.help"), self.theme)

        language_box = tk.Checkbutton(
            frame,
            text=tr("prefs.language") + ("  ✓ English" if language_var.get() else "  ✓ ไทย"),
            variable=language_var,
            bg=self.theme.panel,
            fg=self.theme.foreground,
            selectcolor=self.theme.background,
            activebackground=self.theme.panel,
            activeforeground=self.theme.foreground,
            highlightthickness=0,
            font=(self.theme.monospace_font, 9),
            anchor="w",
            justify="left",
            wraplength=460,
            command=lambda: self._save_language_preference(setter, language_var),
        )
        language_box.grid(row=4, column=0, sticky="w")
        _attach_tip(language_box, tr("prefs.language.help"), self.theme)
        tk.Label(
            frame,
            text=tr("prefs.language.restart"),
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 8),
            anchor="w",
            wraplength=460,
            justify="left",
        ).grid(row=5, column=0, sticky="w", pady=(2, 8))

        self._button(frame, tr("btn.close"), lambda: window.destroy() if window.winfo_exists() else None).grid(
            row=6, column=0, sticky="w"
        )
        return window

    def _save_shutdown_preference(self, setter, var: tk.BooleanVar) -> None:
        try:
            setter("shutdown_stops_instances", var.get())
        except Exception:
            self._handle_error("PREFERENCE_SAVE_FAILED")
            return
        self.log_activity(f"Settings     shutdown_stops={'ON' if var.get() else 'OFF'}")

    def _save_language_preference(self, setter, var: tk.BooleanVar) -> None:
        try:
            setter("language", var.get())
        except Exception:
            self._handle_error("PREFERENCE_SAVE_FAILED")
            return
        set_language("en" if var.get() else "th")
        self.log_activity(f"Settings     language={'en' if var.get() else 'th'}")

    def _save_supervised_preference(self, setter, var: tk.BooleanVar) -> None:
        try:
            setter("supervised", var.get())
        except Exception:
            self._handle_error("PREFERENCE_SAVE_FAILED")
            return
        self.log_activity(f"Settings     supervised={'ON' if var.get() else 'OFF'}")

    def open_guide(self) -> None:
        path = find_user_guide_path()
        if path is None:
            self._handle_error("GUIDE_NOT_FOUND")
            return
        try:
            if self._guide_opener is not None:
                self._guide_opener(path)
                return None
            return self._show_guide_window(path)
        except Exception:
            self._handle_error("GUIDE_OPEN_FAILED")
            return None
        self.log_activity("Guide        opened")

    def _show_guide_window(self, path: Path) -> tk.Toplevel:
        window = tk.Toplevel(self.root)
        window.title(APP_NAME + " — " + tr("win.guide"))
        window.configure(bg=self.theme.background)
        window.geometry("900x640")
        text = tk.Text(
            window,
            bg=self.theme.background,
            fg=self.theme.foreground,
            insertbackground=self.theme.accent,
            wrap="word",
            borderwidth=0,
            highlightthickness=0,
            font=(self.theme.monospace_font, 10),
            padx=14,
            pady=10,
        )
        scroll = ttk.Scrollbar(window, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        content = path.read_text(encoding="utf-8", errors="replace")
        text.insert("1.0", content)
        text.tag_configure(
            "link", foreground=self.theme.accent, underline=True,
        )
        for start, end in link_url_spans(content):
            text.tag_add("link", f"1.0+{start}c", f"1.0+{end}c")
        text.tag_bind(
            "link",
            "<Button-1>",
            lambda event: self._open_guide_link(
                event.widget, event.widget.index(f"@{event.x},{event.y}")
            ),
        )
        text.configure(state="disabled")
        text.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        window.grid_rowconfigure(0, weight=1)
        window.grid_columnconfigure(0, weight=1)
        bar = tk.Frame(window, bg=self.theme.panel)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        self._button(bar, "เปิดไฟล์ภายนอก", lambda: _default_guide_opener(path)).grid(
            row=0, column=0, sticky="w", padx=10, pady=8
        )
        self._button(bar, "ปิด", lambda: window.destroy() if window.winfo_exists() else None).grid(
            row=0, column=1, sticky="w", pady=8
        )
        return window

    def open_worker_config(self) -> tk.Toplevel | None:
        worker_id = self.selected_worker_id()
        if worker_id is None:
            self._handle_error("SELECT_WORKER")
            return None
        load = getattr(self.service, "worker_settings", None)
        save = getattr(self.service, "save_worker_settings", None)
        if not callable(load) or not callable(save):
            self._handle_error("SETTINGS_NOT_AVAILABLE")
            return None
        try:
            settings = load(worker_id)
        except Exception:
            self._handle_error("SETTINGS_LOAD_FAILED")
            return None
        if not isinstance(settings, WorkerSerenaSettings):
            self._handle_error("SETTINGS_RESULT_INVALID")
            return None

        row = self._selected_worker_row()
        bound_project = row.project_root_path if row is not None else ""

        dialog = tk.Toplevel(self.root)
        dialog.title(f"{APP_NAME} — Worker Config — {worker_id}")
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text=f"> WORKER CONFIG  {worker_id}",
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        self._config_worker_id = worker_id
        self._config_entries: dict[str, ttk.Entry | ttk.Combobox] = {}
        blurbs = active_blurbs()
        TOOL_BLURBS = blurbs.TOOL_BLURBS
        LANGUAGE_BLURBS = blurbs.LANGUAGE_BLURBS
        LANGUAGE_BACKEND_BLURBS = blurbs.LANGUAGE_BACKEND_BLURBS
        FIELD_BLURBS = blurbs.FIELD_BLURBS
        MODE_BLURBS = blurbs.MODE_BLURBS

        backend_box = ttk.Combobox(
            frame,
            values=[backend.value for backend in LanguageBackend],
            state="readonly",
            width=30,
        )
        backend_box.set(settings.language_backend.value)
        backend_box.grid(row=1, column=1, sticky="ew", pady=2)
        self._config_entries["language_backend"] = backend_box
        backend_label = tk.Label(
            frame,
            text="Language backend",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        )
        backend_label.grid(row=1, column=0, sticky="w", padx=(0, 10))
        _attach_tip(backend_box, LANGUAGE_BACKEND_BLURBS.get("LSP", ""), self.theme)
        self._backend_blurb = tk.Label(
            frame,
            text="",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 8),
            anchor="w",
        )
        self._backend_blurb.grid(row=2, column=1, sticky="w", pady=(0, 4))

        def update_backend_blurb(*_args):
            value = backend_box.get()
            self._backend_blurb.configure(
                text=LANGUAGE_BACKEND_BLURBS.get(value, "")
            )

        backend_box.bind("<<ComboboxSelected>>", update_backend_blurb)
        update_backend_blurb()

        fields = (
            ("tool_timeout", "Tool timeout (s)", str(settings.tool_timeout)),
            ("project_path", "Project path", settings.project_path or bound_project or ""),
            ("included_optional_tools", "Included optional tools", ",".join(settings.included_optional_tools)),
            ("fixed_tools", "Fixed tools (exclusive)", ",".join(settings.fixed_tools)),
        )
        for row_index, (key, label, value) in enumerate(fields, start=3):
            label_widget = tk.Label(
                frame,
                text=label,
                bg=self.theme.panel,
                fg=self.theme.muted,
                font=(self.theme.monospace_font, 9),
            )
            label_widget.grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=2)
            entry = ttk.Entry(frame, width=56)
            entry.insert(0, value)
            entry.grid(row=row_index, column=1, sticky="ew", pady=2)
            self._config_entries[key] = entry
            blurb = FIELD_BLURBS.get(key, "")
            if blurb:
                _attach_tip(entry, blurb, self.theme)
                _attach_tip(label_widget, blurb, self.theme)
                tk.Label(
                    frame,
                    text=blurb,
                    bg=self.theme.panel,
                    fg=self.theme.muted,
                    font=(self.theme.monospace_font, 8),
                    anchor="w",
                ).grid(row=row_index, column=1, sticky="w", pady=(0, 2))

        next_row = len(fields) + 3

        def toggle_section(
            title: str,
            names: tuple[str, ...],
            initial_on,
            blurbs: dict[str, str] | None = None,
        ) -> dict[str, tk.BooleanVar]:
            nonlocal next_row
            tk.Label(
                frame,
                text=title,
                bg=self.theme.panel,
                fg=self.theme.accent,
                font=(self.theme.monospace_font, 9, "bold"),
            ).grid(row=next_row, column=0, columnspan=2, sticky="w", pady=(10, 2))
            next_row += 1
            vars_by_name: dict[str, tk.BooleanVar] = {}
            columns = 3
            for index, name in enumerate(names):
                var = tk.BooleanVar(value=initial_on(name))
                vars_by_name[name] = var
                row = next_row + index // columns
                column = index % columns
                box = tk.Checkbutton(
                    frame,
                    text=name,
                    variable=var,
                    bg=self.theme.panel,
                    fg=self.theme.foreground,
                    selectcolor=self.theme.background,
                    activebackground=self.theme.panel,
                    activeforeground=self.theme.foreground,
                    highlightthickness=0,
                    font=(self.theme.monospace_font, 9),
                    anchor="w",
                )
                box.grid(row=row, column=column, sticky="w", padx=(0, 18), pady=0)
                blurb = (blurbs or {}).get(name)
                if blurb:
                    _attach_tip(box, f"{name}: {blurb}", self.theme)
            next_row += (len(names) + columns - 1) // columns + 1
            return vars_by_name

        tool_catalog = ENGINE_TOOLS + tuple(
            name
            for name in settings.excluded_tools
            if name not in set(ENGINE_TOOLS)
        )
        excluded_set = set(settings.excluded_tools)
        self._config_tool_vars = toggle_section(
            "TOOLS   ON = enabled, OFF = excluded  (hover ดูคำอธิบายแต่ละตัว)",
            tool_catalog,
            lambda name: name not in excluded_set,
            blurbs=TOOL_BLURBS,
        )
        enabled_langs = set(settings.enabled_languages)
        self._config_lang_vars = toggle_section(
            "LANGUAGES   ON = supported for this project  (hover ดูคำอธิบาย)",
            KNOWN_LANGUAGES,
            lambda name: name in enabled_langs if enabled_langs else True,
            blurbs=LANGUAGE_BLURBS,
        )
        active_modes = set(settings.base_modes)
        self._config_mode_vars = toggle_section(
            "MODES   ON = base mode enabled  (hover ดูคำอธิบาย)",
            tuple(MODE_BLURBS),
            lambda name: name in active_modes,
            blurbs=MODE_BLURBS,
        )

        self._config_status = tk.Label(
            frame,
            text="Values apply on next worker start.",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        )
        self._config_status.grid(row=next_row, column=0, columnspan=2, sticky="w", pady=(8, 0))

        button_row = next_row + 1
        self._button(frame, "Save", lambda: self.save_worker_config(dialog)).grid(
            row=button_row, column=0, sticky="w", pady=(12, 0)
        )
        self._button(frame, "Cancel", lambda: dialog.destroy() if dialog.winfo_exists() else None).grid(
            row=button_row, column=1, sticky="w", pady=(12, 0)
        )
        return dialog

    @staticmethod
    def _csv_field(entry) -> tuple[str, ...]:
        return tuple(part.strip() for part in entry.get().split(",") if part.strip())

    def save_worker_config(self, dialog: tk.Toplevel | None = None) -> None:
        worker_id = getattr(self, "_config_worker_id", None)
        entries = getattr(self, "_config_entries", None)
        save = getattr(self.service, "save_worker_settings", None)
        if worker_id is None or not entries or not callable(save):
            self._handle_error("SETTINGS_NOT_AVAILABLE")
            return

        try:
            backend = LanguageBackend(str(entries["language_backend"].get()).strip())
        except ValueError:
            self._handle_error("SETTINGS_LANGUAGE_BACKEND_INVALID")
            return
        try:
            timeout = int(str(entries["tool_timeout"].get()).strip())
        except ValueError:
            self._handle_error("SETTINGS_TOOL_TIMEOUT_INVALID")
            return

        tool_vars = getattr(self, "_config_tool_vars", None) or {}
        lang_vars = getattr(self, "_config_lang_vars", None) or {}
        excluded_tools = tuple(
            name for name, var in tool_vars.items() if not var.get()
        )
        enabled_languages = tuple(
            name for name, var in lang_vars.items() if var.get()
        )
        project_path = str(entries["project_path"].get()).strip() or None

        try:
            settings = WorkerSerenaSettings(
                worker_id=worker_id,
                language_backend=backend,
                excluded_tools=excluded_tools,
                included_optional_tools=self._csv_field(entries["included_optional_tools"]),
                fixed_tools=self._csv_field(entries["fixed_tools"]),
                base_modes=tuple(
                    name for name, var in self._config_mode_vars.items() if var.get()
                ),
                tool_timeout=timeout,
                project_path=project_path,
                enabled_languages=enabled_languages,
            )
        except ValueError as exc:
            status = getattr(self, "_config_status", None)
            if status is not None and status.winfo_exists():
                status.configure(text=f"ERROR  {exc}", fg=self.theme.error)
            self._handle_error("SETTINGS_INVALID")
            return

        try:
            saved = save(settings)
        except Exception:
            self._handle_error("SETTINGS_SAVE_FAILED")
            return
        if not isinstance(saved, WorkerSerenaSettings):
            self._handle_error("SETTINGS_RESULT_INVALID")
            return
        self.log_activity(f"Config       {saved.worker_id} SAVED (applies on next start)")
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()

    def start_background_operations(self) -> None:
        """Kick instance discovery/health refresh and flagged autostarts.

        Called by the real application entrypoint right before mainloop — not
        during construction — so short-lived constructions (tests, smoke) never
        schedule pool work or timer callbacks on a root that is about to be
        destroyed.
        """
        self.refresh_instances()
        # First-run: open the setup wizard if no connectors exist
        try:
            instances = self.service.instances()
            if not instances:
                self.root.after(1500, self.open_setup_wizard)
        except Exception:
            pass
        self._monitor_tick()
        self._autostart_flagged_instances()

    def _has_instance_service(self) -> bool:
        return all(
            callable(getattr(self.service, name, None))
            for name in (
                "instances",
                "instance_states",
                "instance_action",
                "set_instance_autostart",
            )
        )

    def refresh_instances(self) -> None:
        self._set_enabled(self.brain_button, self._has_settings_service())
        if not self._has_instance_service():
            for button in (
                self.instance_start_button,
                self.instance_stop_button,
                self.instance_startall_button,
                self.instance_auto_button,
                self.instance_rescan_button,
            ):
                self._set_enabled(button, False)
            return
        states_fn = getattr(self.service, "instance_states")
        future = self._background_executor.submit(states_fn)
        self.root.after(0, self._poll_instance_states, future)

    def _poll_instance_states(self, future: Future) -> None:
        if not future.done():
            self.root.after(25, self._poll_instance_states, future)
            return
        try:
            states = future.result()
        except Exception:
            self._handle_error("INSTANCE_REFRESH_FAILED")
            return
        self.instance_tree.delete(*self.instance_tree.get_children())
        self._instance_rows.clear()
        auto_fn = getattr(self.service, "instance_autostart", None)
        aliases_fn = getattr(self.service, "instance_aliases", None)
        aliases: dict[str, str] = {}
        if callable(aliases_fn):
            try:
                aliases = aliases_fn() or {}
            except Exception:
                aliases = {}
        for instance, state in states:
            auto = False
            if callable(auto_fn):
                try:
                    auto = bool(auto_fn(instance.name))
                except Exception:
                    auto = False
            tag = {
                InstanceHealthState.READY.value: "ready",
                InstanceHealthState.STOPPED.value: "idle",
            }.get(state.value, "warning")
            item = self.instance_tree.insert(
                "",
                "end",
                values=(
                    aliases.get(instance.name, instance.name),
                    instance.health_address.split(":")[-1],
                    state.value,
                    instance.project_path,
                    "Y" if instance.tunnel_configured else "-",
                    "ON" if auto else "-",
                ),
                tags=(tag,),
            )
            self._instance_rows[instance.name] = item
            self._monitor_instances[instance.name] = instance
        for button in (
            self.instance_start_button,
            self.instance_stop_button,
            self.instance_startall_button,
            self.instance_auto_button,
            self.instance_rescan_button,
        ):
            self._set_enabled(button, True)
        self._set_enabled(self.brain_button, self._has_settings_service())

    def _selected_instance_name(self) -> str | None:
        selection = self.instance_tree.selection()
        if not selection:
            return None
        for name, item in self._instance_rows.items():
            if item == selection[0]:
                return name
        return None

    def _submit_instance_action(self, action: str, name: str) -> None:
        self.log_activity(f"{action:<12} {name} QUEUED")
        action_fn = getattr(self.service, "instance_action")
        future = self._background_executor.submit(action_fn, name, action.lower())
        self.root.after(0, self._poll_instance_action, action, name, future)

    def _poll_instance_action(self, action: str, name: str, future: Future) -> None:
        if not future.done():
            self.root.after(25, self._poll_instance_action, action, name, future)
            return
        try:
            outcome = future.result()
            code = outcome.result_code.value
        except Exception:
            self._handle_error("INSTANCE_ACTION_FAILED")
            self.refresh_instances()
            return
        self.log_activity(f"{action:<12} {name} {code}")
        self.refresh_instances()

    def start_selected_instance(self) -> None:
        name = self._selected_instance_name()
        if name is None:
            self._handle_error("SELECT_INSTANCE")
            return
        self._submit_instance_action("START-INST", name)

    def stop_selected_instance(self) -> None:
        name = self._selected_instance_name()
        if name is None:
            self._handle_error("SELECT_INSTANCE")
            return
        self._submit_instance_action("STOP-INST", name)

    def start_all_instances(self) -> None:
        if not self._has_instance_service():
            self._handle_error("INSTANCES_NOT_AVAILABLE")
            return
        future = self._background_executor.submit(self._start_all_worker)
        self.root.after(0, self._poll_start_all, future)

    def _start_all_worker(self):
        results: list[tuple[str, str]] = []
        for instance, state in getattr(self.service, "instance_states")():
            if state is InstanceHealthState.READY:
                continue
            try:
                outcome = getattr(self.service, "instance_action")(instance.name, "start")
                results.append((instance.name, outcome.result_code.value))
            except Exception:
                results.append((instance.name, "ERROR"))
        return results

    def _poll_start_all(self, future: Future) -> None:
        if not future.done():
            self.root.after(25, self._poll_start_all, future)
            return
        try:
            results = future.result()
        except Exception:
            self._handle_error("INSTANCE_START_ALL_FAILED")
            self.refresh_instances()
            return
        if not results:
            self.log_activity("START-ALL    all instances already READY")
        for name, code in results:
            self.log_activity(f"START-ALL    {name} {code}")
        self.refresh_instances()

    def toggle_instance_autostart(self) -> None:
        name = self._selected_instance_name()
        if name is None:
            self._handle_error("SELECT_INSTANCE")
            return
        try:
            current = bool(getattr(self.service, "instance_autostart")(name))
            getattr(self.service, "set_instance_autostart")(name, not current)
        except Exception:
            self._handle_error("INSTANCE_FLAG_FAILED")
            return
        item = self._instance_rows.get(name)
        if item is not None and self.instance_tree.exists(item):
            values = list(self.instance_tree.item(item, "values"))
            if len(values) > 5:
                values[5] = "ON" if not current else "-"  # AUTO column (5), not TUNNEL (4)
                self.instance_tree.item(item, values=values)
        self.log_activity(f"AUTO         {name} {'ON' if not current else 'OFF'}")

    def rescan_instances(self) -> None:
        self.log_activity("RESCAN       instances")
        self.refresh_instances()

    def add_instance(self, name: str, project_path: str, tunnel_id: str | None = None) -> None:
        creator = getattr(self.service, "create_instance", None)
        if not callable(creator):
            self._handle_error("INSTANCE_CREATE_NOT_AVAILABLE")
            return
        try:
            instance = creator(name, project_path, tunnel_id)
        except Exception as exc:  # InstanceCreateError carries a machine code
            self._handle_error(getattr(exc, "code", "INSTANCE_CREATE_FAILED"))
            return
        self.log_activity(f"+ Connector  {instance.name}  port={instance.health_address.rsplit(':', 1)[-1]}")
        self.refresh_instances()

    def open_add_instance_dialog(self) -> None:
        creator = getattr(self.service, "create_instance", None)
        if not callable(creator):
            self._handle_error("INSTANCE_CREATE_NOT_AVAILABLE")
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(f'{APP_NAME} — {tr("dlg.add.connector.title")}')
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(1, weight=1)
        tk.Label(
            frame,
            text="> " + tr("dlg.add.connector.header"),
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        tk.Label(
            frame,
            text=tr("dlg.add.connector.name"),
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        ).grid(row=1, column=0, columnspan=2, sticky="w")
        name_entry = ttk.Entry(frame, font=(self.theme.monospace_font, 10))
        name_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 8))
        tk.Label(
            frame,
            text=tr("dlg.add.connector.project"),
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        ).grid(row=3, column=0, columnspan=2, sticky="w")
        project_entry = ttk.Entry(frame, font=(self.theme.monospace_font, 10))
        project_entry.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 8))
        tk.Label(
            frame,
            text=tr("dlg.add.connector.tunnel"),
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        ).grid(row=5, column=0, columnspan=2, sticky="w")
        tunnel_entry = ttk.Entry(frame, font=(self.theme.monospace_font, 10))
        tunnel_entry.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(4, 10))

        def submit() -> None:
            name = name_entry.get().strip()
            project = project_entry.get().strip()
            tunnel = tunnel_entry.get().strip()
            if not name or not project:
                self._handle_error("INSTANCE_FIELDS_REQUIRED")
                return
            dialog.destroy()
            self.add_instance(name, project, tunnel or None)

        name_entry.bind("<Return>", lambda _event: submit())
        project_entry.bind("<Return>", lambda _event: submit())
        self._button(frame, tr("dlg.add.connector.submit"), submit).grid(row=7, column=1, sticky="e")
        name_entry.focus_set()

    def rename_selected_instance(self, new_name: str) -> None:
        name = self._selected_instance_name()
        if name is None:
            self._handle_error("SELECT_INSTANCE")
            return
        writer = getattr(self.service, "rename_instance", None)
        if not callable(writer):
            self._handle_error("INSTANCE_RENAME_NOT_AVAILABLE")
            return
        try:
            display = writer(name, new_name)
        except Exception as exc:
            self._handle_error(getattr(exc, "code", "INSTANCE_RENAME_FAILED"))
            return
        self.log_activity(f"Rename       {name} -> {display}")
        self.refresh_instances()

    def open_rename_instance_dialog(self) -> None:
        name = self._selected_instance_name()
        if name is None:
            self._handle_error("SELECT_INSTANCE")
            return
        aliases = {}
        loader = getattr(self.service, "instance_aliases", None)
        if callable(loader):
            try:
                aliases = loader() or {}
            except Exception:
                aliases = {}
        current = aliases.get(name, name)

        dialog = tk.Toplevel(self.root)
        dialog.title(f'{APP_NAME} — {tr("dlg.rename.connector.title")} — {name}')
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(1, weight=1)
        tk.Label(
            frame,
            text="> " + tr("dlg.rename.header") + f"  {name}",
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        tk.Label(
            frame,
            text=tr("dlg.rename.worker.name").replace("WORKERS", "CONNECTORS"),
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        ).grid(row=1, column=0, columnspan=2, sticky="w")
        name_entry = ttk.Entry(frame, font=(self.theme.monospace_font, 10))
        name_entry.insert(0, current)
        name_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 10))

        def submit() -> None:
            value = name_entry.get().strip()
            if not value:
                self._handle_error("INSTANCE_FIELDS_REQUIRED")
                return
            dialog.destroy()
            self.rename_selected_instance(value)

        name_entry.bind("<Return>", lambda _event: submit())
        self._button(frame, tr("dlg.rename.worker.submit"), submit).grid(row=3, column=1, sticky="e")
        name_entry.focus_set()

    def delete_selected_instance(self, backup_dir=None) -> None:
        name = self._selected_instance_name()
        if name is None:
            self._handle_error("SELECT_INSTANCE")
            return
        remover = getattr(self.service, "delete_instance", None)
        if not callable(remover):
            self._handle_error("INSTANCE_DELETE_NOT_AVAILABLE")
            return
        if not self._confirm(tr("dlg.delete.connector.message").format(name=name)):
            return
        try:
            zip_path = remover(name, backup_dir=backup_dir)
        except Exception as exc:
            self._handle_error(getattr(exc, "code", "INSTANCE_DELETE_FAILED"))
            return
        self.log_activity(f"- Connector  {name}  backup={zip_path}")
        self.refresh_instances()

    def open_brain_config(self) -> tk.Toplevel | None:
        load = getattr(self.service, "worker_settings", None)
        save = getattr(self.service, "save_worker_settings", None)
        if not callable(load) or not callable(save):
            self._handle_error("SETTINGS_NOT_AVAILABLE")
            return None
        try:
            profile = load("global-brain")
        except Exception:
            self._handle_error("SETTINGS_LOAD_FAILED")
            return None
        if not isinstance(profile, WorkerSerenaSettings):
            self._handle_error("SETTINGS_RESULT_INVALID")
            return None

        dialog = tk.Toplevel(self.root)
        dialog.title(APP_NAME + " — Second Brain")
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        tk.Label(
            frame,
            text="> SECOND BRAIN  (ทุก agent ที่เชื่อมเข้ามาต้องอ่านสมองนี้ก่อน)",
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        folders = list(profile.brain_folders) + ["", ""]
        entries = list(profile.brain_entry_files) + ["", ""]
        self._brain_entries: dict[str, ttk.Entry] = {}
        rows = (
            ("brain_folder_1", "Brain folder 1", folders[0]),
            ("brain_folder_2", "Brain folder 2", folders[1]),
            ("brain_entry_1", "ต้องอ่านไฟล์ 1", entries[0]),
            ("brain_entry_2", "ต้องอ่านไฟล์ 2", entries[1]),
        )
        for row_index, (key, label, value) in enumerate(rows, start=1):
            tk.Label(
                frame,
                text=label,
                bg=self.theme.panel,
                fg=self.theme.muted,
                font=(self.theme.monospace_font, 9),
            ).grid(row=row_index, column=0, sticky="w", padx=(0, 10), pady=2)
            entry = ttk.Entry(frame, width=64)
            entry.insert(0, value)
            entry.grid(row=row_index, column=1, sticky="ew", pady=2)
            self._brain_entries[key] = entry
            if key.startswith("brain_folder"):
                self._button(
                    frame,
                    "เลือก...",
                    lambda k=key: self._brain_entries[k].insert(
                        0, self._directory_picker()
                    ),
                ).grid(row=row_index, column=2, sticky="w", padx=(6, 0))

        self._brain_profile_base = profile
        self._brain_status = tk.Label(
            frame,
            text="Index เท่านั้น (ประหยัด token) — agents จะ read_file เพิ่มเมื่อจำเป็น",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        )
        self._brain_status.grid(row=5, column=0, columnspan=3, sticky="w", pady=(8, 0))

        button_row = 6
        self._button(frame, "ใช้ค่า default (A-Wiki)", self._fill_brain_defaults).grid(
            row=button_row, column=0, sticky="w", pady=(12, 0)
        )
        self._button(frame, "Save", lambda: self.save_brain_config(dialog)).grid(
            row=button_row, column=1, sticky="w", pady=(12, 0)
        )
        self._button(frame, "Cancel", lambda: dialog.destroy() if dialog.winfo_exists() else None).grid(
            row=button_row, column=2, sticky="w", pady=(12, 0)
        )
        return dialog

    def _fill_brain_defaults(self) -> None:
        self._brain_entries["brain_folder_1"].delete(0, "end")
        self._brain_entries["brain_folder_1"].insert(0, r"A:\GitHub\A-Wiki")
        self._brain_entries["brain_folder_2"].delete(0, "end")
        self._brain_entries["brain_entry_1"].delete(0, "end")
        self._brain_entries["brain_entry_1"].insert(0, r"A:\GitHub\A-Wiki\AGENTS.md")
        self._brain_entries["brain_entry_2"].delete(0, "end")
        self._brain_entries["brain_entry_2"].insert(
            0, r"A:\GitHub\A-Wiki\wiki\context\wiki-overview.md"
        )

    def save_brain_config(self, dialog: tk.Toplevel | None = None) -> None:
        save = getattr(self.service, "save_worker_settings", None)
        base = getattr(self, "_brain_profile_base", None)
        entries = getattr(self, "_brain_entries", None)
        if base is None or entries is None or not callable(save):
            self._handle_error("SETTINGS_NOT_AVAILABLE")
            return

        def value(key: str) -> str:
            return str(entries[key].get()).strip()

        folders = tuple(v for v in (value("brain_folder_1"), value("brain_folder_2")) if v)
        entry_files = tuple(
            v for v in (value("brain_entry_1"), value("brain_entry_2")) if v
        )
        try:
            updated = replace(
                base,
                brain_folders=folders,
                brain_entry_files=entry_files,
            )
        except ValueError as exc:
            status = getattr(self, "_brain_status", None)
            if status is not None and status.winfo_exists():
                status.configure(text=f"ERROR  {exc}", fg=self.theme.error)
            self._handle_error("SETTINGS_INVALID")
            return
        try:
            saved = save(updated)
        except Exception:
            self._handle_error("SETTINGS_SAVE_FAILED")
            return
        if not isinstance(saved, WorkerSerenaSettings):
            self._handle_error("SETTINGS_RESULT_INVALID")
            return
        self.log_activity(
            f"Brain        {' -> '.join(saved.brain_folders) if saved.brain_folders else 'cleared'} SAVED"
        )
        if dialog is not None and dialog.winfo_exists():
            dialog.destroy()

    def _autostart_flagged_instances(self) -> None:
        if not self._has_instance_service():
            return
        if not callable(getattr(self.service, "autostart_instance_names", None)):
            return
        future = self._background_executor.submit(self._autostart_worker)
        self.root.after(0, self._poll_autostart, future)

    def _autostart_worker(self):
        results: list[tuple[str, str]] = []
        for name in getattr(self.service, "autostart_instance_names")():
            try:
                outcome = getattr(self.service, "instance_action")(name, "start")
                results.append((name, outcome.result_code.value))
            except Exception:
                results.append((name, "ERROR"))
        return results

    def _poll_autostart(self, future: Future) -> None:
        if not future.done():
            self.root.after(25, self._poll_autostart, future)
            return
        try:
            results = future.result()
        except Exception:
            return
        for name, code in results:
            self.log_activity(f"AUTO-START   {name} {code}")
        if results:
            self.refresh_instances()

    def _validate_tunnel_entry(self) -> None:
        value = self._tunnel_entry.get().strip()
        if not value:
            self._tunnel_status.configure(text="", fg=self.theme.muted)
        elif _TUNNEL_ID_RE.fullmatch(value):
            self._tunnel_status.configure(text="รูปแบบถูกต้อง", fg=self.theme.ready)
        else:
            self._tunnel_status.configure(
                text="รูปแบบยังไม่ถูก (tunnel_ + 32 ตัวอักษร)", fg=self.theme.error
            )

    def open_rebind_dialog(self) -> tk.Toplevel | None:
        name = self._selected_instance_name()
        if name is None:
            self._handle_error("SELECT_INSTANCE")
            return None
        rebind_fn = getattr(self.service, "rebind_instance", None)
        if not callable(rebind_fn):
            self._handle_error("REBIND_NOT_AVAILABLE")
            return None

        dialog = tk.Toplevel(self.root)
        dialog.title(f"{APP_NAME} — เปลี่ยนโปรเจกต์ — {name}")
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=16, pady=14)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(1, weight=1)
        tk.Label(
            frame,
            text=f"> เปลี่ยนโปรเจกต์ของ {name}",
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        tk.Label(
            frame,
            text="พาธโปรเจกต์ใหม่ (ต้องมีอยู่จริงในเครื่อง)\nสำรองไฟล์เดิมเป็น .bak อัตโนมัติ · มีผลหลัง restart ตัวเชื่อม",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self._rebind_entry = ttk.Entry(frame, width=64)
        self._rebind_entry.grid(row=2, column=0, sticky="ew", pady=2)
        self._button(
            frame,
            "เลือกโฟลเดอร์...",
            lambda: self._rebind_entry.insert(0, self._directory_picker()),
        ).grid(row=2, column=1, sticky="w", padx=(6, 0))
        self._rebind_status = tk.Label(
            frame, text="", bg=self.theme.panel, fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        )
        self._rebind_status.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        def do_rebind():
            value = self._rebind_entry.get().strip()
            try:
                result = rebind_fn(name, value)
            except Exception:
                self._handle_error("REBIND_FAILED")
                return
            if result != "REBOUND":
                self._rebind_status.configure(
                    text=f"ผลลัพธ์: {result} (ยังไม่ได้เปลี่ยน)", fg=self.theme.warning
                )
                return
            self.log_activity(f"Rebind       {name} -> {value} (restart ตัวเชื่อมเพื่อให้มีผล)")
            if dialog.winfo_exists():
                dialog.destroy()
            self.refresh_instances()

        self._button(frame, "เปลี่ยนเลย", do_rebind).grid(row=4, column=0, sticky="w", pady=(12, 0))
        self._button(
            frame, "ยกเลิก", lambda: dialog.destroy() if dialog.winfo_exists() else None
        ).grid(row=4, column=1, sticky="w", pady=(12, 0))
        return dialog

    def open_tunnel_id_dialog(self) -> tk.Toplevel | None:
        name = self._selected_instance_name()
        if name is None:
            self._handle_error("SELECT_INSTANCE")
            return None
        writer = getattr(self.service, "set_instance_tunnel_id", None)
        if not callable(writer):
            self._handle_error("TUNNEL_SETUP_NOT_AVAILABLE")
            return None

        dialog = tk.Toplevel(self.root)
        dialog.title(f"{APP_NAME} — ตั้ง Tunnel ID — {name}")
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(1, weight=1)
        tk.Label(
            frame,
            text=f"> TUNNEL ID  {name}",
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        tk.Label(
            frame,
            text="วาง Tunnel ID (ขึ้นต้นด้วย tunnel_ ตามด้วย 32 ตัวอักษร)\nวิธีขอ ID: กดปุ่ม คู่มือ → หมวด 'เชื่อมต่อ AI แต่ละค่าย'",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self._tunnel_entry = ttk.Entry(frame, width=52)
        self._tunnel_entry.grid(row=2, column=0, sticky="ew", pady=2)
        self._tunnel_entry.focus_set()
        self._tunnel_status = tk.Label(
            frame,
            text="",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        )
        self._tunnel_status.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self._tunnel_entry.bind("<KeyRelease>", lambda _e: self._validate_tunnel_entry())

        def save():
            value = self._tunnel_entry.get().strip()
            try:
                writer(name, value)
            except Exception:
                self._handle_error("TUNNEL_ID_INVALID")
                return
            self.log_activity(f"Tunnel       {name} ID SAVED")
            if dialog.winfo_exists():
                dialog.destroy()
            self.refresh_instances()

        self._button(frame, "บันทึก", save).grid(row=4, column=0, sticky="w", pady=(12, 0))
        self._button(
            frame, "ยกเลิก", lambda: dialog.destroy() if dialog.winfo_exists() else None
        ).grid(row=4, column=1, sticky="w", pady=(12, 0))
        return dialog

    def check_upstream(self) -> None:
        """Read-only upstream engine update check (first network egress)."""
        self.log_activity("Upstream     checking engine (GitHub)...")
        self._set_enabled(self.upstream_button, False)

        def worker():
            return fetch_upstream_status()

        def present(status):
            self._set_enabled(self.upstream_button, True)
            window = tk.Toplevel(self.root)
            window.title(APP_NAME + " — เช็คอัปเดท engine")
            window.configure(bg=self.theme.panel)
            window.transient(self.root)
            window.resizable(True, False)
            frame = tk.Frame(window, bg=self.theme.panel, padx=16, pady=14)
            frame.pack(fill="both", expand=True)
            frame.grid_columnconfigure(0, weight=1)
            tk.Label(
                frame,
                text="> ENGINE UPSTREAM (Serena)",
                bg=self.theme.panel,
                fg=self.theme.accent,
                font=(self.theme.monospace_font, 10, "bold"),
            ).grid(row=0, column=0, sticky="w", pady=(0, 8))

            lines = []
            if status.error_code:
                lines.append(f"เชื่อมต่อไม่สำเร็จ ({status.error_code}) — เช็คเน็ต/ลองใหม่")
                self.log_activity(f"Upstream     {status.error_code}")
            else:
                if status.latest_release_tag:
                    lines.append(f"Release ล่าสุด:  {status.latest_release_tag}")
                if status.latest_commit_sha:
                    lines.append(f"Commit ล่าสุด:   {status.latest_commit_sha}  ({status.latest_commit_date or ''})")
                lines.append("ถ้ามีเวอร์ชันใหม่ ให้ AI agent อ่าน release notes แล้วช่วยอัปเดทตาม")
                self.log_activity(
                    f"Upstream     release={status.latest_release_tag} commit={status.latest_commit_sha}"
                )
            text = tk.Text(
                frame,
                bg=self.theme.background,
                fg=self.theme.foreground,
                insertbackground=self.theme.accent,
                wrap="word",
                borderwidth=0,
                highlightthickness=0,
                font=(self.theme.monospace_font, 10),
                padx=12,
                pady=8,
                height=max(4, len(lines) + 1),
                width=60,
            )
            content = chr(10).join(lines)
            if status.repo_url:
                content += chr(10) + status.repo_url
            text.insert("1.0", content)
            text.tag_configure("link", foreground=self.theme.accent, underline=True)
            for start, end in link_url_spans(content):
                text.tag_add("link", f"1.0+{start}c", f"1.0+{end}c")
            text.tag_bind(
                "link",
                "<Button-1>",
                lambda event: self._open_guide_link(
                    event.widget, event.widget.index(f"@{event.x},{event.y}")
                ),
            )
            text.configure(state="disabled")
            text.grid(row=1, column=0, sticky="ew")
            self._button(
                frame, "ปิด", lambda: window.destroy() if window.winfo_exists() else None
            ).grid(row=2, column=0, sticky="w", pady=(10, 0))

        future = self._background_executor.submit(worker)
        self.root.after(
            0,
            lambda: self._poll_upstream(future, present),
        )

    def _poll_upstream(self, future: Future, present) -> None:
        if not future.done():
            self.root.after(25, lambda: self._poll_upstream(future, present))
            return
        try:
            status = future.result()
        except Exception:
            self._set_enabled(self.upstream_button, True)
            self._handle_error("UPSTREAM_CHECK_FAILED")
            return
        present(status)
