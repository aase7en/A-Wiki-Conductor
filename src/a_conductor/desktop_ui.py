"""Tkinter desktop adapter for the A-Sunday Conductor control center.

The desktop layer consumes only the application-service snapshot/actions. It
contains no process, tunnel, Git, or persistence implementation.
"""

from __future__ import annotations

import os
import re
import sys
from concurrent.futures import CancelledError, Executor, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Event
from typing import Callable, Protocol

import tkinter as tk
from tkinter import filedialog, simpledialog, ttk
import webbrowser

from .branding import APP_NAME, APP_VERSION
from .connector_recovery import ConnectorRecoveryRecord
from .graph.domain import TaskNodeStatus
from .graph.operator_view import GraphOperatorSnapshot
from .error_explanations_en import ERROR_EXPLANATIONS_EN
from .i18n import canonical_button_label, get_language, set_language, tr
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
from .system_metrics import SystemMetricsSampler, format_memory, format_percent, format_uptime


def find_user_guide_path() -> Path | None:
    """Locate the bundled user guide (repo layout in dev, bundle dir frozen).

    Follows the UI language: USER-GUIDE-EN.md when English is active and
    available, otherwise the Thai USER-GUIDE.md.
    """
    from .i18n import get_language

    names = ["USER-GUIDE.md"]
    if get_language() in {"en", "zh-CN"}:
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


def find_particle_image_path() -> Path | None:
    """Prefer the user-facing family particle portrait, then the legacy logo."""
    asset_dirs: list[Path] = []
    if getattr(sys, "frozen", False):
        asset_dirs.append(Path(sys.executable).resolve().parent / "assets")
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        asset_dirs.append(Path(bundle) / "assets")
    asset_dirs.append(Path(__file__).resolve().parents[2] / "assets")
    for asset_dir in asset_dirs:
        for name in ("sunday-family-particle.png", "logo-face.png"):
            candidate = asset_dir / name
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
    "ASSIGNMENT_CONFLICT": (
        "Assignment ชนกับงานที่มีอยู่",
        (
            "ขาด: โปรเจกต์หรือ worktree ใหม่นี้ถูก Worker อื่นถือสิทธิ์แก้ไขอยู่ หรือ assignment ใหม่ไม่เข้ากัน",
            "ทำอย่างไร: เลือก Worker/โปรเจกต์ที่ไม่ชนกัน หรือหยุดงานเดิมก่อน แล้วลอง Assign ใหม่",
        ),
    ),
    "REGISTRY_NOT_FOUND": (
        "ไม่พบ Worker หรือ Project ในสถานะล่าสุด",
        (
            "ขาด: รายการที่เลือกไม่อยู่ใน registry ล่าสุดแล้ว",
            "ทำอย่างไร: กด Refresh แล้วเลือก Project และ Worker ใหม่ก่อนลองอีกครั้ง",
        ),
    ),
    "WORKER_BUSY": (
        "Worker กำลังทำงานอยู่",
        (
            "ขาด: Worker ต้องอยู่ในสถานะ STOPPED ก่อนเปลี่ยนโปรเจกต์",
            "ทำอย่างไร: กด Stop แล้วกด Assign โปรเจกต์ใหม่อีกครั้ง ระบบจะถามยืนยันก่อนแทนที่",
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
    "PROVIDER_STORE_NOT_AVAILABLE": (
        "ควบคุม Provider ไม่ได้",
        ("ไม่พบ provider store ที่ระบบเก็บไว้", "ให้เปิด Settings ใหม่หรือรีสตาร์ตโปรแกรม; ยังไม่มีการแก้ provider"),
    ),
    "PROVIDER_GENERATION_STALE": (
        "ข้อมูล Provider เปลี่ยนไปแล้ว",
        ("หน้าจอนี้ใช้ generation เก่ากว่าข้อมูลที่บันทึก", "กด Refresh ตรวจค่าล่าสุดแล้วค่อยลองใหม่"),
    ),
    "PROVIDER_GENERATION_EXPECTED": (
        "ต้องมี Provider generation",
        ("การแก้ไขแบบปลอดภัยต้องใช้ generation ที่อ่านมา", "กด Refresh แล้วลองใหม่หนึ่งครั้ง"),
    ),
    "PROVIDER_GENERATION_EXHAUSTED": (
        "Provider generation เต็มแล้ว",
        ("ตัวนับ generation ไม่สามารถเพิ่มได้อีก", "หยุดแก้ไขและเก็บฐานข้อมูลไว้ตรวจสอบ"),
    ),
    "PROVIDER_CONFIGURATION_IN_USE": (
        "Provider กำลังถูกใช้งาน",
        ("มี admission ที่ ACTIVE หรือยังไม่ reconcile", "รอให้งานจบ/reconcile แล้วกด Refresh ก่อนลองใหม่"),
    ),
    "PROVIDER_PROFILE_INVALID": (
        "ข้อมูลที่แก้ไข Provider ไม่ถูกต้อง",
        ("มีช่องที่ไม่ผ่าน validation", "แก้ค่าที่กรอกให้ถูกต้อง; หน้านี้จะไม่แสดง secret หรือ endpoint"),
    ),
    "PROVIDER_TEST_TARGET_UNAVAILABLE": (
        "เป้าหมาย Test ไม่พร้อม",
        ("provider, endpoint หรือ generation หายไปก่อนเริ่ม Test", "กด Refresh แล้วเลือก provider ใหม่"),
    ),
    "PROVIDER_OBSERVATION_GENERATION_STALE": (
        "ผล Test ล้าสมัย",
        ("configuration เปลี่ยนระหว่าง Test", "กด Refresh แล้ว Test ใหม่เฉพาะเมื่อ configuration ใหม่ยังต้องตรวจ"),
    ),
    "PROVIDER_CONFIGURATION_CORRUPT": (
        "ข้อมูล Provider เสียหาย",
        ("ข้อมูลที่บันทึกไม่ผ่าน typed decoding", "อย่าแก้จากหน้านี้; ใช้ recovery path ที่ระบบกำหนด"),
    ),
    "CONFIG_STORE_UNAVAILABLE": (
        "เปิดฐานข้อมูล Provider ไม่ได้",
        ("ไม่พบหรือเปิด control database ของ provider ไม่ได้", "ตรวจ path/สิทธิ์ของ control database แล้วกด Refresh"),
    ),
    "CONFIG_STORE_SCHEMA_UNAVAILABLE": (
        "Provider schema ไม่พร้อม",
        ("ฐานข้อมูล control ไม่มี schema ที่ต้องใช้", "เปิดแอปเวอร์ชันปัจจุบันกับ control database ที่ถูกต้อง"),
    ),
    "CONFIG_STORE_READ_FAILED": (
        "อ่านฐานข้อมูล Provider ไม่สำเร็จ",
        ("SQLite อ่าน provider configuration ไม่ได้", "กด Refresh; ถ้ายังซ้ำให้ตรวจ control database และ log"),
    ),
    "PROVIDER_ACTION_FAILED": (
        "คำสั่ง Provider ไม่สำเร็จ",
        ("คำสั่งจบด้วยข้อผิดพลาดที่ไม่คาดไว้", "กด Refresh และดู ACTIVITY / LOG ก่อนลองใหม่"),
    ),
    "PROVIDER_EVIDENCE_TARGET_UNAVAILABLE": (
        "เป้าหมายหลักฐาน Provider ไม่พร้อม",
        ("provider หายไปก่อนที่จะอ่านหลักฐานได้", "กด Refresh แล้วเลือก provider ใหม่อีกครั้ง"),
    ),
    "PROVIDER_ADMISSION_RECORD_INVALID": (
        "ระเบียน admission เสียหาย",
        ("ข้อมูล admission ที่บันทึกไว้ไม่ผ่าน typed decoding", "หยุดการอ่านหลักฐาน; ซ่อมข้อมูลที่บันทึกผ่าน recovery path ที่ระบบกำหนด"),
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
        tree.bind("<Destroy>", self._hide, add="+")

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

    def __init__(self, widget, text: str | Callable[[], str], theme: "DesktopTheme") -> None:
        self.widget = widget
        self.text = text
        self.theme = theme
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<FocusIn>", self._show, add="+")
        widget.bind("<FocusOut>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        text = self.text() if callable(self.text) else self.text
        if self.tip is not None or not text or not text.strip():
            return
        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self.tip = window = tk.Toplevel(self.widget)
        window.wm_overrideredirect(True)
        window.wm_geometry(f"+{x}+{y}")
        tk.Label(
            window,
            text=text,
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


def _attach_tip(widget, text: str | Callable[[], str], theme: "DesktopTheme"):
    widget._acond_tooltip = ToolTip(widget, text, theme)
    return widget


def responsive_column_count(width: int, button_count: int, target_button_width: int = 110) -> int:
    """Return a stable number of action columns from actual available width."""
    if button_count <= 0:
        return 0
    usable = max(1, int(width))
    target = max(72, int(target_button_width))
    return max(1, min(button_count, usable // target))


def _monitor_safe_text(value: str, limit: int = 72) -> str:
    text = " ".join(str(value).split())
    if len(text) <= limit:
        return text
    return text[: max(1, limit - 1)] + "…"


def graph_monitor_lines(snapshot: GraphOperatorSnapshot) -> tuple[str, ...]:
    if not isinstance(snapshot, GraphOperatorSnapshot):
        raise ValueError("snapshot must be GraphOperatorSnapshot")
    counts = {status: 0 for status in TaskNodeStatus}
    for node in snapshot.nodes:
        counts[node.status] += 1
    lines = ["MONITOR · GRAPH", f"  GRAPH {snapshot.graph_id}"]
    if snapshot.runtime_evidence:
        lines.append(
            f"  RUN {snapshot.graph_run_id}   RUNTIME: DURABLE RUN EVIDENCE"
        )
    elif snapshot.graph_run_id:
        lines.append(f"  RUN {snapshot.graph_run_id}   RUNTIME: NO RUN EVIDENCE")
    else:
        lines.append("  RUNTIME: NO RUN EVIDENCE")
    lines.append(
        "  QUEUE "
        f"TODO {counts[TaskNodeStatus.TODO]}   "
        f"DOING {counts[TaskNodeStatus.DOING]}   "
        f"BLOCKED {counts[TaskNodeStatus.BLOCKED]}   "
        f"DONE {counts[TaskNodeStatus.DONE]}   "
        f"SKIPPED {counts[TaskNodeStatus.SKIPPED]}"
    )

    lines.append("  --- nodes ---")
    for node in snapshot.nodes:
        worker = f" worker={node.worker_id}" if node.worker_id else ""
        lines.append(
            f"  {node.status.name:<7} {node.node_id}{worker}  "
            f"{_monitor_safe_text(node.objective)}"
        )
    lines.append("  --- edges ---")
    if snapshot.edges:
        lines.extend(
            f"  {edge.from_id} -> {edge.to_id} [{edge.dependency_type.value}]"
            for edge in snapshot.edges
        )
    else:
        lines.append("  -")
    lines.append("  --- timeline ---")
    if not snapshot.runtime_evidence:
        lines.append("  timeline: - (explicit run required)")
    elif not snapshot.events:
        lines.append("  timeline: -")
    else:
        for event in snapshot.events:
            transition = ""
            if event.from_state or event.to_state:
                transition = f" {event.from_state or '-'}->{event.to_state or '-'}"
            worker = f" worker={event.worker_id}" if event.worker_id else ""
            lines.append(
                f"  {event.recorded_at} {event.node_id} {event.event_type}"
                f"{transition}{worker}"
            )
    return tuple(lines)


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

    def replace_assignment(
        self,
        worker_id: str,
        project_id: str,
        *,
        mutation_allowed: bool = True,
    ): ...

    def release_worker(self, worker_id: str): ...


@dataclass(frozen=True, slots=True)
class DesktopTheme:
    background: str = "#080b0f"
    panel: str = "#0d1117"
    panel_alt: str = "#11161d"
    border: str = "#242b35"
    foreground: str = "#d8dee6"
    muted: str = "#7d8794"
    accent: str = "#78a9e6"
    ready: str = "#66c985"
    ready_dim: str = "#4f9a67"
    warning: str = "#ddb45f"
    error: str = "#df6b72"
    idle: str = "#808995"
    selection: str = "#172331"
    monospace_font: str = "Cascadia Mono"
    sans_font: str = "Segoe UI"
    base_font_size: int = 10


def provider_graph_evidence_links(snapshot, graph_id: str | None, graph_run_id: str | None) -> dict[str, str]:
    """Exact-match execution_id -> node_id map for one explicit graph/run.

    Pure derivation over an existing read-only graph operator snapshot.
    No graph search, no latest-run inference, no substring matching; missing
    explicit context yields no links at all.
    """
    if (
        not graph_id
        or not graph_run_id
        or snapshot is None
        or not bool(getattr(snapshot, "runtime_evidence", False))
    ):
        return {}
    from .graph.dispatch import GraphDispatchKey

    links: dict[str, str] = {}
    for node in tuple(getattr(snapshot, "nodes", ()) or ()):
        node_id = getattr(node, "node_id", None)
        if not isinstance(node_id, str) or not node_id.strip():
            continue
        try:
            job_id = GraphDispatchKey(graph_id, graph_run_id, node_id).job_id
        except (TypeError, ValueError):
            continue
        links[job_id] = node_id
    return links


class AConductorDesktopApp:
    SYSTEM_METRIC_INTERVAL_MS = 2500
    SYSTEM_METRIC_HISTORY_LIMIT = 60

    def __init__(
        self,
        root: tk.Tk,
        *,
        service: ControlCenterUIService,
        theme: DesktopTheme | None = None,
        directory_picker: Callable[[], str] | None = None,
        error_handler: Callable[[str], None] | None = None,
        background_executor: Executor | None = None,
        disk_executor: Executor | None = None,
        guide_opener: Callable[[Path], None] | None = None,
        guide_html_frame_factory: Callable | None = None,
        guide_url_opener: Callable[[str], object] | None = None,
    ) -> None:
        self.root = root
        self.service = service
        self.theme = theme or DesktopTheme()
        self._directory_picker = directory_picker or filedialog.askdirectory
        self._error_handler = error_handler or self._show_error
        self._guide_opener = guide_opener
        self._guide_html_frame_factory = guide_html_frame_factory
        self._guide_url_opener = guide_url_opener or webbrowser.open
        self._background_executor = background_executor or ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="a-conductor-ui"
        )
        self._owns_background_executor = background_executor is None
        self._background_cancel_event = Event()
        self._project_disk_executor = disk_executor or ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="a-conductor-disk"
        )
        self._owns_project_disk_executor = disk_executor is None
        self._project_disk_future: Future | None = None
        self._project_disk_cancel_event: Event | None = None
        self._project_disk_request_id = 0
        self._project_disk_request_path: str | None = None
        self._project_disk_cache: dict[str, str] = {}
        self._instance_start_futures: set[Future] = set()
        self._project_ids: list[str] = []
        self._project_paths: dict[str, str] = {}
        self._worker_ids: dict[str, str] = {}
        self._setup_entries: dict[str, ttk.Entry] = {}
        self._setup_draft: WorkerSetupDraft | None = None
        self._instance_rows: dict[str, str] = {}
        self._row_path_tip_providers: dict = {}
        self._row_path_menu_label_providers: dict = {}
        self._monitor_instances: dict = {}
        self._system_metrics_sampler = SystemMetricsSampler()
        self._system_metric_after_id = None
        self._cpu_history: list[float] = []
        self._closing = False
        self._ui_resources_stopped = False
        self._scheduled_after_ids: set[str] = set()
        self._status_pulse_after_id = None
        self._monitor_tick_after_id = None
        self._monitor_poll_after_id = None
        self._instance_refresh_after_id = None
        self._instance_states_active = False
        self._rescan_summary_pending = False
        self._monitor_future: Future | None = None
        self._monitor_refresh_pending = False
        self._monitor_mode = "connector"
        self._graph_monitor_graph_id: str | None = None
        self._graph_monitor_run_id: str | None = None
        self._pane_layout_after_id = None
        self._activity_align_after_id = None
        self._pane_layout_height = 0
        self._worker_counts = (0, 0)
        self._connector_counts = (0, 0)
        self._active_drift_count = 0
        self._worker_registry_expanded = False
        self._preferences_window: tk.Toplevel | None = None
        self._models_agents_refresh_pending = False
        self._models_agents_request_id = 0
        self._models_agents_future: Future | None = None
        self._models_agents_last_rows: tuple = ()
        self._models_agents_last_error: str | None = None
        self._models_agents_loading = False
        self._models_agents_provider_ids: tuple[str, ...] = ()
        self._models_agents_action_request_id = 0
        self._models_agents_action_future: Future | None = None
        self._models_agents_action_pending_provider: str | None = None
        self._models_agents_action_message = ""
        self._provider_edit_window: tk.Toplevel | None = None
        self._provider_evidence_window: tk.Toplevel | None = None
        self._provider_evidence_provider_id: str | None = None
        self._provider_evidence_cache = None
        self._provider_evidence_request_id = 0
        self._provider_evidence_future: Future | None = None
        self._provider_evidence_pending = False

        self._configure_root()
        self._configure_styles()
        self._build_layout()
        self.refresh()

    def _configure_root(self) -> None:
        pref_getter = getattr(self.service, "get_preference", None)
        if callable(pref_getter):
            try:
                if pref_getter("language_zh"):
                    set_language("zh-CN")
                elif pref_getter("language"):
                    set_language("en")
                else:
                    set_language("th")
            except Exception:
                set_language("th")
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_request)
        self.root.bind("<Destroy>", self._on_root_destroy, add="+")
        self.root.configure(background=self.theme.background)
        self.root.geometry("1080x680")
        # The three operational tiers (workers, connectors, monitor/log) cannot
        # remain usable below this height without hiding controls.  Constrain
        # the real window instead of allowing Tk's PanedWindow to collapse a
        # tier to a few pixels.
        self.root.minsize(700, 680)
        icon = find_icon_path()
        if icon is not None:
            try:
                self.root.iconbitmap(str(icon))
            except tk.TclError:
                pass

    def _schedule_after(self, delay_ms: int, callback, *args) -> str | None:
        """Schedule one owned Tk callback so shutdown can cancel it deterministically."""
        if self._closing:
            return None
        holder: dict[str, str] = {}

        def invoke() -> None:
            callback_id = holder.get("id")
            if callback_id is not None:
                self._scheduled_after_ids.discard(callback_id)
            if self._closing:
                return
            callback(*args)

        try:
            callback_id = self.root.after(max(0, int(delay_ms)), invoke)
        except tk.TclError:
            return None
        holder["id"] = callback_id
        self._scheduled_after_ids.add(callback_id)
        return callback_id

    def _cancel_after(self, callback_id: str | None) -> None:
        if callback_id is None:
            return
        self._scheduled_after_ids.discard(callback_id)
        try:
            self.root.after_cancel(callback_id)
        except (tk.TclError, ValueError):
            pass

    def _cancel_all_scheduled_callbacks(self) -> None:
        for callback_id in tuple(self._scheduled_after_ids):
            self._cancel_after(callback_id)

    def _shutdown_ui_resources(self) -> None:
        if self._ui_resources_stopped:
            return
        self._ui_resources_stopped = True
        self._background_cancel_event.set()
        self._cancel_project_disk_scan()
        self._stop_teaching_animation()
        self._stop_system_monitor()
        self._stop_status_pulse()
        self._stop_instance_monitor()
        self._cancel_after(self._pane_layout_after_id)
        self._pane_layout_after_id = None
        self._cancel_after(self._activity_align_after_id)
        self._activity_align_after_id = None
        self._cancel_all_scheduled_callbacks()
        logo = getattr(self, "_logo", None)
        if logo is not None:
            try:
                logo.destroy()
            except Exception:
                pass
        if self._owns_project_disk_executor:
            try:
                self._project_disk_executor.shutdown(wait=False, cancel_futures=True)
            except (RuntimeError, TypeError):
                pass
        if self._owns_background_executor:
            try:
                self._background_executor.shutdown(wait=False, cancel_futures=True)
            except (RuntimeError, TypeError):
                pass

    def _on_root_destroy(self, event) -> None:
        if event.widget is not self.root:
            return
        self._closing = True
        self._shutdown_ui_resources()

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
            padding=(2, 2),
            font=(self.theme.monospace_font, max(8, self.theme.base_font_size - 2)),
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
            rowheight=25,
            font=(self.theme.monospace_font, max(8, self.theme.base_font_size - 1)),
        )
        style.configure(
            "Workers.Treeview.Heading",
            background=self.theme.panel_alt,
            foreground=self.theme.muted,
            bordercolor=self.theme.border,
            font=(self.theme.monospace_font, max(8, self.theme.base_font_size - 1), "bold"),
        )
        style.map(
            "Workers.Treeview",
            background=[("selected", self.theme.selection)],
            foreground=[("selected", self.theme.foreground)],
        )
        # PROJECTS rows render two lines (display name + root path), so the
        # sidebar tree needs a taller rowheight; Treeview never auto-sizes.
        style.configure(
            "Projects.Treeview",
            background=self.theme.panel,
            fieldbackground=self.theme.panel,
            foreground=self.theme.foreground,
            bordercolor=self.theme.border,
            rowheight=40,
            font=(self.theme.monospace_font, max(8, self.theme.base_font_size - 1)),
        )
        style.configure(
            "Projects.Treeview.Heading",
            background=self.theme.panel_alt,
            foreground=self.theme.muted,
            bordercolor=self.theme.border,
            font=(self.theme.monospace_font, max(8, self.theme.base_font_size - 1), "bold"),
        )
        style.map(
            "Projects.Treeview",
            background=[("selected", self.theme.selection)],
            foreground=[("selected", self.theme.foreground)],
        )

    def _build_layout(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(3, weight=1)

        top = tk.Frame(
            self.root,
            bg=self.theme.panel,
            highlightthickness=1,
            highlightbackground=self.theme.border,
        )
        self._header_frame = top
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=(4, 2))
        top.grid_columnconfigure(3, weight=1)

        try:
            from .gpu_particle_logo import GPUParticleLogo

            self._logo = GPUParticleLogo(top, size=120)
            self._logo.grid(row=0, column=0, sticky="w", padx=(10, 8), pady=0)
            logo_path = find_particle_image_path()
            if logo_path is not None:
                self._logo.load_image(logo_path)
            self._logo.start()
            _attach_tip(self._logo.canvas, lambda: tr("tip.logo"), self.theme)
        except Exception:
            self._logo = None

        brand = tk.Frame(top, bg=self.theme.panel)
        self._brand_frame = brand
        brand.grid(row=0, column=1, sticky="w", padx=(2, 10), pady=7)
        self.title_label = tk.Label(
            brand,
            text="A-CONDUCTOR",
            bg=self.theme.panel,
            fg=self.theme.foreground,
            font=(self.theme.monospace_font, 18, "bold"),
            anchor="w",
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        self.tagline_label = tk.Label(
            brand,
            text="Orchestrate. Execute. Observe.",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
            anchor="w",
        )
        self.tagline_label.grid(row=1, column=0, sticky="w", pady=(2, 4))
        status_strip = tk.Frame(brand, bg=self.theme.panel)
        status_strip.grid(row=2, column=0, sticky="w")
        self.connection_label = tk.Label(
            status_strip,
            text="● ONLINE",
            bg=self.theme.background,
            fg=self.theme.ready,
            font=(self.theme.monospace_font, 8, "bold"),
            padx=7,
            pady=2,
            highlightthickness=1,
            highlightbackground=self.theme.border,
        )
        self.connection_label.pack(side="left")
        _attach_tip(self.connection_label, lambda: tr("tip.connection"), self.theme)
        self.header_runtime_label = tk.Label(
            status_strip,
            text="SLOTS —  · REGISTRY —",
            bg=self.theme.background,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 8),
            padx=7,
            pady=2,
            highlightthickness=1,
            highlightbackground=self.theme.border,
        )
        self.header_runtime_label.pack(side="left", padx=(5, 0))

        self.brain_button = self._button(top, "Add Brain", self.open_brain_config)
        self.brain_button.grid(row=0, column=2, sticky="w", padx=(0, 8), pady=6)
        _attach_tip(self.brain_button, lambda: tr("tip.brain"), self.theme)

        header_actions = tk.Frame(top, bg=self.theme.panel)
        self._header_actions = header_actions
        header_actions.grid(row=0, column=4, sticky="e", padx=(0, 10), pady=5)
        self.help_button = self._button(header_actions, "Guide", self.open_guide)
        _attach_tip(self.help_button, lambda: tr("tip.guide"), self.theme)
        self.prefs_button = self._button(header_actions, "Settings", self.open_preferences)
        _attach_tip(self.prefs_button, lambda: tr("tip.settings"), self.theme)

        header_action_state = {"compact": None}

        def _reflow_header_actions(event=None) -> None:
            width = getattr(event, "width", None) or top.winfo_width()
            compact = int(width) < 760
            if header_action_state["compact"] is compact:
                return
            header_action_state["compact"] = compact
            self.help_button.grid_forget()
            self.prefs_button.grid_forget()
            self.help_button.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 3 if compact else 0))
            self.prefs_button.grid(
                row=1 if compact else 0,
                column=0 if compact else 1,
                sticky="ew",
                padx=(0, 0) if compact else (4, 0),
                pady=0,
            )

        top.bind("<Configure>", _reflow_header_actions, add="+")
        self._schedule_after(0, _reflow_header_actions)

        if not all(
            callable(getattr(self.service, name, None))
            for name in ("get_preference", "set_preference")
        ):
            self.prefs_button.state(["disabled"])

        self._teaching_label = tk.Label(
            self.root,
            text="",
            bg=self.theme.background,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
            anchor="w",
            height=1,
        )
        self._teaching_label.grid(row=1, column=0, sticky="ew", padx=14, pady=0)
        self._restart_teaching_animation()

        workflow = tk.Frame(self.root, bg=self.theme.background)
        workflow.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 2))
        self._workflow_frame = workflow
        self.add_button = self._button(workflow, "Add Project", self.add_project)
        self.assign_button = self._button(workflow, "Assign Worker", self.assign_selected)
        self.add_worker_button = self._button(workflow, "Add Worker", self.open_add_worker_dialog)
        self.start_button = self._button(workflow, "Start Worker", self.start_selected)
        self.stop_button = self._button(workflow, "Stop Worker", self.stop_selected)
        self.restart_button = self._button(workflow, "Restart Worker", self.restart_selected)
        self.release_button = self._button(workflow, "Release Worker", self.release_selected)
        self.activate_button = self._button(workflow, "Copy Activate", self.copy_activation_prompt)
        self.refresh_button = self._button(workflow, "Refresh", self.refresh)
        self.workflow_buttons = (
            self.add_button, self.assign_button, self.add_worker_button,
            self.start_button, self.stop_button, self.restart_button,
            self.release_button, self.activate_button, self.refresh_button,
        )
        for button, key in (
            (self.add_button, "tip.add.project"),
            (self.assign_button, "tip.assign"),
            (self.add_worker_button, "tip.add.worker"),
            (self.start_button, "tip.start"),
            (self.stop_button, "tip.stop"),
            (self.restart_button, "tip.restart"),
            (self.release_button, "tip.release"),
            (self.activate_button, "tip.activate"),
            (self.refresh_button, "tip.refresh"),
        ):
            _attach_tip(button, lambda k=key: tr(k), self.theme)
        self._make_responsive_action_grid(workflow, self.workflow_buttons, target_button_width=96)

        self._main_pane = ttk.PanedWindow(self.root, orient="vertical")
        self._main_pane.grid(row=3, column=0, sticky="nsew", padx=6, pady=2)
        self._body_pane = ttk.PanedWindow(self._main_pane, orient="horizontal")
        self._main_pane.add(self._body_pane, weight=3)

        project_panel = self._panel(self._body_pane, "PROJECTS")
        self._body_pane.add(project_panel, weight=0)
        project_panel.grid_rowconfigure(1, weight=1)
        project_panel.grid_columnconfigure(0, weight=1)
        project_columns = ("project", "edit")
        # Treeview (not Listbox) so every row can carry an inline Edit
        # action cell and an empty table can show a "+ Add Project" row.
        self.project_list = ttk.Treeview(
            project_panel,
            columns=project_columns,
            show="headings",
            selectmode="browse",
            style="Projects.Treeview",
            height=4,
        )
        self.project_list.heading("project", text="PROJECT", anchor="w")
        # Small base widths keep the sidebar's requested width near the old
        # Listbox footprint; stretch=True lets the column fill the pane.
        self.project_list.column("project", width=100, minwidth=80, anchor="w", stretch=True)
        self.project_list.heading("edit", text="EDIT", anchor="w")
        self.project_list.column("edit", width=44, minwidth=40, anchor="w", stretch=False)
        self._project_edit_column = f"#{len(project_columns)}"
        project_scroll = ttk.Scrollbar(
            project_panel, orient="vertical", command=self.project_list.yview
        )
        self.project_list.configure(yscrollcommand=project_scroll.set)
        self.project_list.grid(row=1, column=0, sticky="nsew", padx=(9, 0), pady=(0, 4))
        project_scroll.grid(row=1, column=1, sticky="ns", padx=(0, 9), pady=(0, 4))
        self.project_list.tag_configure("row-add", foreground=self.theme.accent)

        self.memory_status_label = tk.Label(
            project_panel,
            text=tr("memory.select"),
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
            lambda: tr("tip.memory"),
            self.theme,
        )
        self.project_list.bind(
            "<<TreeviewSelect>>", lambda _event: self._refresh_memory_status()
        )
        self.project_list.bind(
            "<Button-1>", self._on_project_tree_click, add=True
        )

        right_stack = tk.Frame(self._body_pane, bg=self.theme.background)
        self._right_stack = right_stack
        self._body_pane.add(right_stack, weight=1)
        right_stack.grid_columnconfigure(0, weight=1)
        right_stack.grid_rowconfigure(1, weight=0)

        overview_panel = self._panel(right_stack, "SYSTEM OVERVIEW")
        self._overview_frame = overview_panel
        overview_panel.grid(row=0, column=0, sticky="ew", padx=(4, 0), pady=(0, 4))
        overview_panel.grid_columnconfigure(0, weight=1)
        metrics = tk.Frame(overview_panel, bg=self.theme.panel)
        metrics.grid(row=1, column=0, sticky="ew", padx=9, pady=(0, 4))
        for col in range(4):
            metrics.grid_columnconfigure(col, weight=1)

        def _overview_metric(column: int, label: str):
            cell = tk.Frame(metrics, bg=self.theme.panel)
            cell.grid(row=0, column=column, sticky="ew", padx=(0, 10 if column < 3 else 0))
            caption = tk.Label(
                cell, text=label, bg=self.theme.panel, fg=self.theme.muted,
                font=(self.theme.monospace_font, 8), anchor="w",
            )
            caption.pack(side="left", anchor="w")
            value = tk.Label(
                cell, text="—", bg=self.theme.panel, fg=self.theme.foreground,
                font=(self.theme.monospace_font, 12, "bold"), anchor="w",
            )
            value.pack(side="left", anchor="w", padx=(6, 0))
            return caption, value

        projects_caption, self.overview_projects_value = _overview_metric(0, "PROJECTS")
        workers_caption, self.overview_workers_value = _overview_metric(1, "AI SLOTS LIVE")
        connectors_caption, self.overview_connectors_value = _overview_metric(
            2, "ACTIVE DRIFT"
        )
        self.overview_connectors_value.configure(text="0 / 0")
        state_caption, self.overview_state_value = _overview_metric(3, "CONTROLLER")
        # WO-P1-070/073: exact project disk size + bounded visual magnitude cue.
        disk_caption, self.overview_disk_value = _overview_metric(4, "PROJECT DISK")
        self._project_disk_particles = tk.Canvas(
            self.overview_disk_value.master,
            width=98,
            height=16,
            bg=self.theme.panel,
            bd=0,
            highlightthickness=0,
        )
        self._project_disk_particles.pack(side="left", anchor="w", padx=(7, 0))
        _attach_tip(
            self._project_disk_particles,
            lambda: tr("tip.project.disk"),
            self.theme,
        )
        self._draw_project_disk_particles("—")
        self._make_responsive_metric_grid(
            metrics,
            tuple(
                value.master
                for value in (
                    self.overview_projects_value,
                    self.overview_workers_value,
                    self.overview_connectors_value,
                    self.overview_state_value,
                    self.overview_disk_value,
                )
            ),
            captions=(
                projects_caption,
                workers_caption,
                connectors_caption,
                state_caption,
                disk_caption,
            ),
            full_labels=("PROJECTS", "AI SLOTS LIVE", "ACTIVE DRIFT", "CONTROLLER"),
            compact_labels=("PROJECTS", "SLOTS", "DRIFT", "STATE"),
        )

        system_strip = tk.Frame(overview_panel, bg=self.theme.panel)
        self._system_metrics_frame = system_strip
        system_strip.grid(row=2, column=0, sticky="ew", padx=9, pady=(0, 5))
        system_strip.grid_columnconfigure(3, weight=1)

        def _system_metric_cell(column: int, label: str, width: int):
            cell = tk.Frame(system_strip, bg=self.theme.panel)
            cell.grid(row=0, column=column, sticky="w", padx=(0, 12))
            tk.Label(
                cell, text=label, bg=self.theme.panel, fg=self.theme.muted,
                font=(self.theme.monospace_font, 8), anchor="w",
            ).pack(side="left", anchor="w")
            value = tk.Label(
                cell, text="—", bg=self.theme.panel, fg=self.theme.foreground,
                font=(self.theme.monospace_font, 10, "bold"), anchor="w", width=width,
            )
            value.pack(side="left", anchor="w", padx=(5, 0))
            return value

        self.overview_cpu_value = _system_metric_cell(0, "CPU", 6)
        self.overview_memory_value = _system_metric_cell(1, "MEMORY", 17)
        self.overview_uptime_value = _system_metric_cell(2, "UPTIME", 12)
        self._cpu_sparkline = tk.Canvas(
            system_strip, width=150, height=24, bg=self.theme.panel,
            highlightthickness=0, bd=0, takefocus=0,
        )
        self._cpu_sparkline.grid(row=0, column=3, sticky="ew", padx=(4, 0))

        worker_panel = self._panel(right_stack, "SCHEDULER REGISTRY [ADVANCED]")
        self._worker_panel = worker_panel
        worker_panel.grid(row=1, column=0, sticky="ew", padx=(4, 0))
        worker_panel.grid_rowconfigure(2, weight=1)
        worker_panel.grid_columnconfigure(0, weight=1)
        self.registry_status_label = tk.Label(
            worker_panel,
            text="Logical scheduler state · hidden by default",
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 8),
            anchor="w",
        )
        self.registry_status_label.grid(row=1, column=0, sticky="ew", padx=9, pady=(0, 2))
        self.registry_toggle_button = self._button(
            worker_panel, "Show Registry", self.toggle_worker_registry
        )
        self.registry_toggle_button.grid(row=0, column=1, sticky="e", padx=(4, 9), pady=1)
        columns = ("worker", "state", "project", "path", "connector", "edit")
        self.worker_tree = ttk.Treeview(
            worker_panel,
            columns=columns,
            show="headings",
            selectmode="browse",
            style="Workers.Treeview",
            # Keep PanedWindow's requested height compact. The pane expands
            # with available space; a large Treeview default otherwise starves
            # CONNECTORS and the console at the minimum supported window.
            height=1,
        )
        headings = {
            "worker": ("WORKER", 110),
            "state": ("SCHED STATE", 95),
            "project": ("PROJECT", 155),
            "path": ("PATH", 235),
            "connector": ("MATCHED CONNECTOR", 150),
            "edit": ("EDIT", 48),
        }
        for name, (label, width) in headings.items():
            self.worker_tree.heading(name, text=label, anchor="w")
            self.worker_tree.column(name, width=width, minwidth=48, anchor="w")
        self._worker_edit_column = f"#{len(columns)}"
        worker_scroll = ttk.Scrollbar(worker_panel, orient="vertical", command=self.worker_tree.yview)
        self.worker_tree.configure(yscrollcommand=worker_scroll.set)
        self.worker_tree.grid(row=2, column=0, sticky="nsew", padx=(9, 0), pady=(0, 2))
        worker_scroll.grid(row=2, column=1, sticky="ns", padx=(0, 9), pady=(0, 2))
        self.worker_xscroll = ttk.Scrollbar(
            worker_panel, orient="horizontal", command=self.worker_tree.xview
        )
        self.worker_tree.configure(xscrollcommand=self.worker_xscroll.set)
        self.worker_xscroll.grid(row=3, column=0, sticky="ew", padx=(9, 0), pady=(0, 2))
        self.worker_tree.bind("<<TreeviewSelect>>", lambda _event: self._update_lifecycle_buttons())
        self.worker_tree.tag_configure("ready", foreground=self.theme.ready)
        self.worker_tree.tag_configure("warning", foreground=self.theme.warning)
        self.worker_tree.tag_configure("error", foreground=self.theme.error)
        self.worker_tree.tag_configure("idle", foreground=self.theme.idle)
        self.worker_tree.tag_configure("row-add", foreground=self.theme.accent)
        self.worker_tree.bind("<Button-1>", self._on_worker_tree_click, add=True)
        self._attach_row_path_tip(
            self.worker_tree, column=3, label=lambda: tr("menu.copy.path")
        )
        _attach_tip(self.worker_tree, lambda: self.connector_help_text(), self.theme)

        actions = tk.Frame(worker_panel, bg=self.theme.panel)
        actions.grid(row=4, column=0, columnspan=2, sticky="ew", padx=9, pady=(1, 3))
        self.setup_button = self._button(actions, "Setup", self.open_runtime_setup)
        self.config_button = self._button(actions, "Config", self.open_worker_config)
        self.rename_worker_button = self._button(actions, "Rename", self.open_rename_worker_dialog)
        self.delete_worker_button = self._button(actions, "Delete", self.delete_selected_worker)
        for button, key in (
            (self.setup_button, "tip.setup"),
            (self.config_button, "tip.config"),
            (self.rename_worker_button, "tip.rename.worker"),
            (self.delete_worker_button, "tip.delete.worker"),
        ):
            _attach_tip(button, lambda k=key: tr(k), self.theme)
        self._make_responsive_action_grid(
            actions,
            (self.setup_button, self.config_button, self.rename_worker_button, self.delete_worker_button),
            target_button_width=105,
        )
        self._worker_registry_widgets = (
            self.worker_tree, worker_scroll, self.worker_xscroll, actions
        )
        for widget in self._worker_registry_widgets:
            widget.grid_remove()
        _attach_tip(self.registry_toggle_button, lambda: tr("tip.worker.registry"), self.theme)
        self.start_button.state(["disabled"])
        self.stop_button.state(["disabled"])
        self.restart_button.state(["disabled"])
        self.setup_button.state(["disabled"])
        self.config_button.state(["disabled"])

        instances_panel = self._panel(self._main_pane, "AI EXECUTION SLOTS — LIVE ≤15s")
        self._main_pane.add(instances_panel, weight=1)
        instances_panel.grid_columnconfigure(0, weight=1)
        instances_panel.grid_rowconfigure(1, weight=1)
        instance_columns = ("name", "port", "state", "project", "tunnel", "auto", "active_project", "last_switch", "edit")
        self.instance_tree = ttk.Treeview(
            instances_panel,
            columns=instance_columns,
            show="headings",
            selectmode="browse",
            style="Workers.Treeview",
            height=1,
        )
        instance_headings = {
            "name": ("SLOT", 150),
            "port": ("PORT", 65),
            "state": ("CONNECTION", 90),
            "project": ("BOUND PROJECT", 220),
            "tunnel": ("TUNNEL", 65),
            "auto": ("AUTO", 55),
            "edit": ("EDIT", 48),
            "active_project": ("ACTIVE PROJECT", 170),
            "last_switch": ("LAST SWITCH", 90),
        }
        for name, (label, width) in instance_headings.items():
            self.instance_tree.heading(name, text=label, anchor="w")
            self.instance_tree.column(name, width=width, minwidth=48, anchor="w")
        self.instance_tree.configure(
            displaycolumns=(
                "name", "state", "active_project", "project",
                "last_switch", "port", "tunnel", "auto", "edit",
            )
        )
        self._instance_edit_column = f"#{len(instance_columns)}"
        self.instance_tree.tag_configure("row-add", foreground=self.theme.accent)
        self.instance_tree.bind("<Button-1>", self._on_instance_tree_click, add=True)
        self.instance_tree.grid(row=1, column=0, sticky="nsew", padx=9, pady=(0, 1))
        self.instance_xscroll = ttk.Scrollbar(
            instances_panel, orient="horizontal", command=self.instance_tree.xview
        )
        self.instance_tree.configure(xscrollcommand=self.instance_xscroll.set)
        self.instance_xscroll.grid(row=2, column=0, sticky="ew", padx=9, pady=(0, 1))
        self.instance_tree.tag_configure("ready", foreground=self.theme.ready)
        self.instance_tree.tag_configure("warning", foreground=self.theme.warning)
        self.instance_tree.tag_configure("idle", foreground=self.theme.idle)
        _attach_tip(self.instance_tree, lambda: tr("tip.execution.slots"), self.theme)
        self._attach_row_path_tip(
            self.instance_tree, column=3, label=lambda: tr("menu.copy.path")
        )

        instance_actions = tk.Frame(instances_panel, bg=self.theme.panel)
        instance_actions.grid(row=3, column=0, sticky="ew", padx=9, pady=(0, 2))
        self.instance_start_button = self._button(instance_actions, "Start Connector", self.start_selected_instance)
        self.instance_stop_button = self._button(instance_actions, "Stop Connector", self.stop_selected_instance)
        self.instance_startall_button = self._button(instance_actions, "Start All", self.start_all_instances)
        self.instance_auto_button = self._button(instance_actions, "Toggle Auto", self.toggle_instance_autostart)
        self.instance_rescan_button = self._button(instance_actions, "Rescan", self.rescan_instances)
        self.add_instance_button = self._button(instance_actions, "Add Connector", self.open_add_instance_dialog)
        self.rename_instance_button = self._button(instance_actions, "Rename", self.open_rename_instance_dialog)
        self.delete_instance_button = self._button(instance_actions, "Delete", self.delete_selected_instance)
        self.tunnel_button = self._button(instance_actions, "Set Tunnel ID", self.open_tunnel_id_dialog)
        self.rebind_button = self._button(instance_actions, "Change Project", self.open_rebind_dialog)
        self.upstream_button = self._button(instance_actions, "Check Engine Update", self.check_upstream)
        connector_buttons = (
            self.instance_start_button, self.instance_stop_button, self.instance_startall_button,
            self.instance_auto_button, self.instance_rescan_button, self.add_instance_button,
            self.rename_instance_button, self.delete_instance_button, self.tunnel_button,
            self.rebind_button, self.upstream_button,
        )
        connector_tip_keys = (
            "tip.instance.start", "tip.instance.stop", "tip.instance.startall",
            "tip.instance.auto", "tip.instance.rescan", "tip.add.connector",
            "tip.rename.connector", "tip.delete.connector", "tip.tunnel",
            "tip.rebind", "tip.upstream",
        )
        for button, key in zip(connector_buttons, connector_tip_keys):
            _attach_tip(button, lambda k=key: tr(k), self.theme)
        self._make_responsive_action_grid(instance_actions, connector_buttons, target_button_width=116)
        for button in (
            self.instance_start_button, self.instance_stop_button, self.instance_startall_button,
            self.instance_auto_button, self.instance_rescan_button, self.tunnel_button,
            self.rebind_button,
        ):
            button.state(["disabled"])
        self._set_enabled(self.upstream_button, True)

        self._lower_pane = ttk.PanedWindow(self._main_pane, orient="horizontal")
        self._main_pane.add(self._lower_pane, weight=2)
        monitor_panel = self._panel(self._lower_pane, "MONITOR")
        self._lower_pane.add(monitor_panel, weight=1)
        monitor_panel.grid_columnconfigure(0, weight=1)
        monitor_panel.grid_rowconfigure(1, weight=1)
        self.monitor_text = tk.Text(
            monitor_panel,
            height=1,
            bg=self.theme.background,
            fg=self.theme.foreground,
            borderwidth=0,
            highlightthickness=0,
            wrap="none",
            state="disabled",
            font=(self.theme.monospace_font, self.theme.base_font_size),
        )
        self.monitor_text.grid(row=1, column=0, sticky="nsew", padx=(9, 0), pady=(0, 1))
        self._enable_copyable_text(self.monitor_text)
        self._graph_monitor_button = self._button(
            monitor_panel, "Graph...", self.open_graph_monitor
        )
        self._connector_monitor_button = self._button(
            monitor_panel, "Connector", self.show_connector_monitor
        )
        self._graph_monitor_button.grid(row=0, column=1, sticky="e", padx=(4, 0), pady=1)
        self._connector_monitor_button.grid(
            row=0, column=2, sticky="e", padx=(4, 0), pady=1
        )
        self._button(
            monitor_panel, "Copy All", lambda: self.copy_text_widget_all(self.monitor_text)
        ).grid(row=0, column=3, sticky="e", padx=(4, 9), pady=1)
        self.instance_tree.bind(
            "<<TreeviewSelect>>", lambda _event: self._refresh_monitor_async(), add="+"
        )
        self._update_monitor_now()

        # Status bar (bottom, full-width) — brand watermark + update button
        status_bar = tk.Frame(self.root, bg=self.theme.background, height=24)
        status_bar.grid(row=4, column=0, sticky="ew", padx=0, pady=(0, 2))
        self._update_button = self._button(status_bar, "Check Update", self.check_for_updates)
        self._donate_button = self._button(status_bar, "Donate", self.open_donate_dialog)
        self._update_button.pack(side="right", padx=(4, 10), pady=2)
        self._donate_button.pack(side="right", padx=(4, 0), pady=2)
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
        self.brand_label.pack(side="left", padx=(8, 4))
        self.brand_label.bind(
            "<Button-1>",
            lambda _e: webbrowser.open("https://github.com/aase7en/A-Wiki-Conductor"),
        )

        activity_panel = self._panel(self._lower_pane, "ACTIVITY / LOG")
        self._lower_pane.add(activity_panel, weight=1)
        self._main_pane.bind("<Map>", self._queue_main_pane_layout, add="+")
        self._main_pane.bind("<Configure>", self._queue_main_pane_layout, add="+")
        self._queue_main_pane_layout()
        activity_panel.grid_rowconfigure(1, weight=1)
        activity_panel.grid_columnconfigure(0, weight=1)
        self.activity_text = tk.Text(
            activity_panel,
            height=1,
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
        self.activity_text.grid(row=1, column=0, sticky="nsew", padx=(9, 0), pady=(0, 1))
        self.activity_text.bind(
            "<Configure>", self._queue_activity_alignment, add="+"
        )
        self._enable_copyable_text(self.activity_text)
        self._button(
            activity_panel, "Copy All", lambda: self.copy_text_widget_all(self.activity_text)
        ).grid(row=0, column=1, sticky="e", padx=(4, 9), pady=1)
        activity_scroll.grid(row=1, column=1, sticky="ns", padx=(0, 9), pady=(0, 1))
        self.log_activity("Control Center ready")
        self._status_pulse_after_id = self._schedule_after(1200, self._start_status_pulse)

    def _connector_recovery_for_monitor(
        self, instance_name: str
    ) -> ConnectorRecoveryRecord | None:
        recovery_fn = getattr(self.service, "connector_recovery_record", None)
        if not callable(recovery_fn):
            return None
        try:
            recovery = recovery_fn(instance_name)
        except Exception:
            return None
        return recovery if isinstance(recovery, ConnectorRecoveryRecord) else None

    def _monitor_report_with_recovery(self, name: str, target, state: str) -> dict:
        from .instance_monitor import monitor_report

        report = monitor_report(target.instance_root, state=state)
        report["recovery"] = self._connector_recovery_for_monitor(name)
        return report

    @staticmethod
    def _format_recovery_timestamp(value: float | None) -> str:
        if value is None:
            return "-"
        try:
            return (
                datetime.fromtimestamp(float(value), tz=timezone.utc)
                .isoformat(timespec="seconds")
                .replace("+00:00", "Z")
            )
        except (TypeError, ValueError, OSError, OverflowError):
            return "-"

    def open_graph_monitor(self) -> None:
        graph_ids_fn = getattr(self.service, "operator_graph_ids", None)
        if not callable(graph_ids_fn):
            self._error_handler("GRAPH_MONITOR_UNAVAILABLE")
            return
        try:
            graph_ids = tuple(graph_ids_fn())
        except Exception:
            self._error_handler("GRAPH_MONITOR_READ_FAILED")
            return
        if not graph_ids:
            self._error_handler("GRAPH_MONITOR_EMPTY")
            return
        preview = ", ".join(graph_ids[:8])
        initial_graph = self._graph_monitor_graph_id or graph_ids[0]
        graph_id = simpledialog.askstring(
            "Graph Monitor",
            f"GRAPH ID\nAvailable: {preview}",
            initialvalue=initial_graph,
            parent=self.root,
        )
        if graph_id is None:
            return
        graph_id = graph_id.strip()
        if graph_id not in graph_ids:
            self._error_handler("GRAPH_MONITOR_GRAPH_INVALID")
            return
        run_id = simpledialog.askstring(
            "Graph Monitor",
            "RUN ID (optional; blank = planning-only / no run evidence)",
            initialvalue=self._graph_monitor_run_id or "",
            parent=self.root,
        )
        if run_id is None:
            return
        self._monitor_mode = "graph"
        self._graph_monitor_graph_id = graph_id
        self._graph_monitor_run_id = run_id.strip() or None
        self._invalidate_provider_evidence_graph_links()
        self._refresh_monitor_async()

    def show_connector_monitor(self) -> None:
        self._monitor_mode = "connector"
        self._refresh_monitor_async()

    def _render_graph_monitor(
        self,
        snapshot: GraphOperatorSnapshot | None,
        error_code: str | None = None,
    ) -> None:
        if not self.monitor_text.winfo_exists():
            return
        lines = (
            graph_monitor_lines(snapshot)
            if snapshot is not None
            else ("MONITOR · GRAPH", f"  error: {error_code or 'GRAPH_MONITOR_READ_FAILED'}")
        )
        try:
            self.monitor_text.configure(state="normal")
            self.monitor_text.delete("1.0", "end")
            self.monitor_text.insert("1.0", chr(10).join(lines))
            self.monitor_text.yview_moveto(0.0)
            self.monitor_text.configure(state="disabled")
        except tk.TclError:
            pass

    @staticmethod
    def _graph_monitor_error_code(exc: Exception) -> str:
        code = getattr(exc, "code", None)
        if isinstance(code, str) and code.strip() and "\n" not in code and "\r" not in code:
            return code.strip()
        return "GRAPH_MONITOR_READ_FAILED"

    def _update_graph_monitor_now(self) -> None:
        graph_id = getattr(self, "_graph_monitor_graph_id", None)
        if not graph_id:
            self._render_graph_monitor(None, "GRAPH_CONTEXT_REQUIRED")
            return
        snapshot_fn = getattr(self.service, "operator_graph_snapshot", None)
        if not callable(snapshot_fn):
            self._render_graph_monitor(None, "GRAPH_MONITOR_UNAVAILABLE")
            return
        try:
            snapshot = snapshot_fn(graph_id, self._graph_monitor_run_id)
        except Exception as exc:
            self._render_graph_monitor(None, self._graph_monitor_error_code(exc))
            return
        self._render_graph_monitor(snapshot)

    def _update_monitor_now(self) -> None:
        """Sync render (tests / no-selection hint path)."""
        if getattr(self, "_monitor_mode", "connector") == "graph":
            self._update_graph_monitor_now()
            return
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
        self._render_monitor(name, self._monitor_report_with_recovery(name, target, state))

    def _render_monitor(self, name, report) -> None:
        """Paint the MONITOR panel; report=None means unknown/none."""
        if not self.monitor_text.winfo_exists():
            return
        state = report.get("state", "-") if report else "-"
        lines: list[str] = ["MONITOR"]
        if name is None:
            lines.append(tr("monitor.select"))
            lines.append(tr("monitor.select.detail"))
        elif report is None:
            lines.append(tr("monitor.missing").format(name=name))
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
            recovery = report.get("recovery")
            if isinstance(recovery, ConnectorRecoveryRecord):
                suppressed = "YES" if recovery.recovery_suppressed else "NO"
                lines.append(
                    f"  recovery: {recovery.state.value}   "
                    f"restarts {recovery.restart_count}   failures {recovery.failure_count}   "
                    f"suppressed {suppressed}"
                )
                lines.append(
                    f"  last exit: {recovery.last_exit_reason or '-'} @ "
                    f"{self._format_recovery_timestamp(recovery.last_exit_at)}"
                )
                lines.append(
                    f"  next retry: {self._format_recovery_timestamp(recovery.next_retry_at)}"
                )
            else:
                lines.append("  recovery: -")
            lines.append(f"  log: {report['log_file'] or '-'}")
            errors = report["errors"]
            lines.append(tr("monitor.errors").format(count=len(errors)))
            lines.append("  --- tail ---")
            lines.extend(f"  {line}" for line in report["tail"])
        try:
            self.monitor_text.configure(state="normal")
            self.monitor_text.delete("1.0", "end")
            self.monitor_text.insert("1.0", chr(10).join(lines))
            # Replacing a longer report can preserve Tk's previous fractional
            # y-view and leave the new first line half above the viewport.
            self.monitor_text.yview_moveto(0.0)
            self.monitor_text.configure(state="disabled")
        except tk.TclError:
            pass

    def _monitor_tick(self) -> None:
        """Auto-refresh MONITOR while keeping one sampler and one timer in flight."""
        self._cancel_after(self._monitor_tick_after_id)
        self._monitor_tick_after_id = None
        if self._closing:
            return
        try:
            self._refresh_monitor_async()
        except tk.TclError:
            return
        self._monitor_tick_after_id = self._schedule_after(15000, self._monitor_tick)

    def _monitor_target(self, name: str):
        cached = self._monitor_instances.get(name)
        if cached is not None:
            return cached
        return next(
            (item for item in self.service.instances() if item.name == name), None
        )

    def _refresh_monitor_async(self) -> None:
        """Fetch the selected monitor mode off the UI thread, then render."""
        if self._closing:
            return
        if self._monitor_future is not None and not self._monitor_future.done():
            self._monitor_refresh_pending = True
            return
        if getattr(self, "_monitor_mode", "connector") == "graph":
            self._refresh_graph_monitor_async()
            return
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
            return self._monitor_report_with_recovery(name, target, state)

        try:
            future = self._background_executor.submit(work)
        except Exception:
            self._update_monitor_now()
            return
        self._monitor_future = future
        self._monitor_refresh_pending = False
        self._poll_monitor(future, name)

    def _refresh_graph_monitor_async(self) -> None:
        if self._closing:
            return
        if self._monitor_future is not None and not self._monitor_future.done():
            self._monitor_refresh_pending = True
            return
        graph_id = self._graph_monitor_graph_id
        run_id = self._graph_monitor_run_id
        if not graph_id:
            self._update_graph_monitor_now()
            return
        snapshot_fn = getattr(self.service, "operator_graph_snapshot", None)
        if not callable(snapshot_fn):
            self._render_graph_monitor(None, "GRAPH_MONITOR_UNAVAILABLE")
            return

        def work():
            try:
                return snapshot_fn(graph_id, run_id), None
            except Exception as exc:
                return None, self._graph_monitor_error_code(exc)

        try:
            future = self._background_executor.submit(work)
        except Exception:
            self._update_graph_monitor_now()
            return
        self._monitor_future = future
        self._monitor_refresh_pending = False
        self._poll_graph_monitor(future, graph_id, run_id)

    def _poll_graph_monitor(self, future, graph_id: str, run_id: str | None) -> None:
        self._cancel_after(self._monitor_poll_after_id)
        self._monitor_poll_after_id = None
        if self._closing or future is not self._monitor_future:
            return
        if not future.done():
            self._monitor_poll_after_id = self._schedule_after(
                25, self._poll_graph_monitor, future, graph_id, run_id
            )
            return
        self._monitor_future = None
        try:
            snapshot, error_code = future.result()
        except Exception:
            snapshot, error_code = None, "GRAPH_MONITOR_READ_FAILED"
        if (
            not self._closing
            and self._monitor_mode == "graph"
            and self._graph_monitor_graph_id == graph_id
            and self._graph_monitor_run_id == run_id
        ):
            self._render_graph_monitor(snapshot, error_code)
        if self._monitor_refresh_pending and not self._closing:
            self._monitor_refresh_pending = False
            self._schedule_after(0, self._refresh_monitor_async)

    def _poll_monitor(self, future, name: str) -> None:
        self._cancel_after(self._monitor_poll_after_id)
        self._monitor_poll_after_id = None
        if self._closing or future is not self._monitor_future:
            return
        if not future.done():
            self._monitor_poll_after_id = self._schedule_after(
                25, self._poll_monitor, future, name
            )
            return
        self._monitor_future = None
        try:
            report = future.result()
        except Exception:
            report = None
        if (
            not self._closing
            and getattr(self, "_monitor_mode", "connector") == "connector"
            and self._selected_instance_name() == name
        ):
            self._render_monitor(name, report)
        if self._monitor_refresh_pending and not self._closing:
            self._monitor_refresh_pending = False
            self._schedule_after(0, self._refresh_monitor_async)

    def _stop_instance_monitor(self) -> None:
        self._cancel_after(self._monitor_tick_after_id)
        self._cancel_after(self._monitor_poll_after_id)
        self._cancel_after(self._instance_refresh_after_id)
        self._monitor_tick_after_id = None
        self._monitor_poll_after_id = None
        self._instance_refresh_after_id = None
        self._monitor_refresh_pending = False
        future = self._monitor_future
        self._monitor_future = None
        if future is not None and not future.done():
            future.cancel()

    def _instance_refresh_tick(self) -> None:
        """Live connectors-state refresh (15s), mirroring the monitor tick.

        Before WO-P1-068 the CONNECTORS table only updated on Rescan, so
        sessions killed earlier (e.g. by close-time stop-all) kept showing
        READY until the operator manually rescanned."""
        self._cancel_after(self._instance_refresh_after_id)
        self._instance_refresh_after_id = None
        if self._closing or not self._has_instance_service():
            return
        self.refresh_instances()
        self._instance_refresh_after_id = self._schedule_after(
            15000, self._instance_refresh_tick
        )

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
            pady=1,
        ).grid(row=0, column=0, sticky="ew")
        return frame

    def _button(self, parent, text: str, command) -> ttk.Button:
        return ttk.Button(
            parent,
            text=canonical_button_label(text),
            command=command,
            style="AConductor.TButton",
        )

    def _make_responsive_action_grid(
        self, parent: tk.Widget, buttons, *, target_button_width: int = 110
    ) -> None:
        buttons = tuple(buttons)
        state = {"layout": None}

        def reflow(event=None) -> None:
            width = getattr(event, "width", None) or parent.winfo_width()
            available = max(1, int(width))
            requested_widths: list[int] = []
            for button in buttons:
                requested = int(button.winfo_reqwidth())
                if requested <= 1:
                    requested = max(72, int(target_button_width))
                requested_widths.append(requested)
            columns = 1
            for candidate in range(len(buttons), 0, -1):
                column_widths = [0] * candidate
                for index, requested in enumerate(requested_widths):
                    column = index % candidate
                    column_widths[column] = max(column_widths[column], requested)
                if sum(column_widths) + 4 * candidate <= available:
                    columns = candidate
                    break
            layout = [
                (index // columns, index % columns)
                for index in range(len(buttons))
            ]
            packed = tuple(layout)
            if state["layout"] == packed:
                return
            state["layout"] = packed
            for button, (row, column) in zip(buttons, packed):
                button.grid(
                    row=row, column=column,
                    padx=(0, 4), pady=(0, 1), sticky="w",
                )

        parent.bind("<Configure>", reflow, add="+")
        self._schedule_after(0, reflow)

    def _make_responsive_metric_grid(
        self,
        parent: tk.Widget,
        cells,
        *,
        captions,
        full_labels,
        compact_labels,
    ) -> None:
        """Keep compact operational metrics complete instead of truncating text."""
        cells = tuple(cells)
        captions = tuple(captions)
        full_labels = tuple(full_labels)
        compact_labels = tuple(compact_labels)
        state = {"layout": None}

        def reflow(event=None) -> None:
            available = max(
                1,
                int(getattr(event, "width", None) or parent.winfo_width()),
            )
            compact = available < 600
            for caption, text in zip(
                captions,
                compact_labels if compact else full_labels,
            ):
                caption.configure(text=text)
            requested = [max(1, int(cell.winfo_reqwidth())) for cell in cells]
            columns = len(cells) if compact else 1
            if not compact:
                for candidate in (len(cells), 2, 1):
                    column_widths = [0] * candidate
                    for index, width in enumerate(requested):
                        column = index % candidate
                        column_widths[column] = max(column_widths[column], width)
                    if sum(column_widths) + 10 * (candidate - 1) <= available:
                        columns = candidate
                        break
            layout = (columns, compact)
            if state["layout"] == layout:
                return
            state["layout"] = layout
            for column in range(len(cells)):
                parent.grid_columnconfigure(
                    column,
                    weight=1 if column < columns else 0,
                )
            last_row = (len(cells) - 1) // columns
            for index, cell in enumerate(cells):
                row, column = divmod(index, columns)
                cell.grid(
                    row=row,
                    column=column,
                    sticky="ew",
                    padx=(0, 10 if column < columns - 1 else 0),
                    pady=(0, 2 if row < last_row else 0),
                )

        parent.bind("<Configure>", reflow, add="+")
        self._schedule_after(0, reflow)

    def _queue_main_pane_layout(self, _event=None) -> None:
        if self._closing or self._pane_layout_after_id is not None:
            return
        self._pane_layout_after_id = self._schedule_after(0, self._apply_main_pane_layout)

    def _apply_main_pane_layout(self) -> None:
        self._pane_layout_after_id = None
        if self._closing:
            return
        try:
            height = int(self._main_pane.winfo_height())
            if height < 180 or len(self._main_pane.panes()) < 3:
                return
            if abs(height - self._pane_layout_height) < 2:
                return
            first = max(96, int(height * 0.49))
            second = min(int(height * 0.84), height - 70)
            self._main_pane.sashpos(0, first)
            self._main_pane.sashpos(1, max(first + 120, second))
            self._pane_layout_height = height
            # Sash geometry settles on the next Tk turn. Re-align the log then
            # so startup entries written while the pane was tiny remain whole.
            if hasattr(self, "activity_text"):
                self._queue_activity_alignment()
        except tk.TclError:
            return

    def _queue_activity_alignment(self, _event=None) -> None:
        if self._closing or self._activity_align_after_id is not None:
            return
        self._activity_align_after_id = self._schedule_after(
            0, self._run_activity_alignment
        )

    def _run_activity_alignment(self) -> None:
        self._activity_align_after_id = None
        self._align_activity_view()

    @staticmethod
    def _state_tag(state: WorkerState) -> str:
        if state is WorkerState.READY:
            return "ready"
        if state in {WorkerState.STARTING, WorkerState.BUSY, WorkerState.STOPPING}:
            return "warning"
        if state is WorkerState.ERROR:
            return "error"
        return "idle"

    def _draw_cpu_sparkline(self) -> None:
        canvas = getattr(self, "_cpu_sparkline", None)
        if canvas is None or not canvas.winfo_exists():
            return
        try:
            width = max(20, int(canvas.winfo_width() or canvas.winfo_reqwidth()))
            height = max(12, int(canvas.winfo_height() or canvas.winfo_reqheight()))
            canvas.delete("all")
            values = list(self._cpu_history)
            if not values:
                return
            if len(values) == 1:
                y = height - (max(0.0, min(100.0, values[0])) / 100.0) * (height - 4) - 2
                canvas.create_oval(width - 3, y - 1, width - 1, y + 1, fill=self.theme.accent, outline="")
                return
            x_step = (width - 2) / max(1, len(values) - 1)
            points: list[float] = []
            for index, value in enumerate(values):
                x = 1 + index * x_step
                y = height - (max(0.0, min(100.0, value)) / 100.0) * (height - 4) - 2
                points.extend((x, y))
            canvas.create_line(*points, fill=self.theme.accent, width=1, smooth=False)
        except tk.TclError:
            return

    def _update_system_metrics_now(self) -> None:
        try:
            metrics = self._system_metrics_sampler.sample()
        except Exception:
            return
        self.overview_cpu_value.configure(text=format_percent(metrics.cpu_percent))
        self.overview_memory_value.configure(
            text=format_memory(metrics.memory_used_bytes, metrics.memory_total_bytes)
        )
        self.overview_uptime_value.configure(text=format_uptime(metrics.uptime_seconds))
        if metrics.cpu_percent is not None:
            self._cpu_history.append(max(0.0, min(100.0, float(metrics.cpu_percent))))
            if len(self._cpu_history) > self.SYSTEM_METRIC_HISTORY_LIMIT:
                del self._cpu_history[:-self.SYSTEM_METRIC_HISTORY_LIMIT]
        self._draw_cpu_sparkline()

    def _system_monitor_tick(self) -> None:
        self._system_metric_after_id = None
        if getattr(self, "_closing", False):
            return
        self._update_system_metrics_now()
        try:
            self._system_metric_after_id = self._schedule_after(
                self.SYSTEM_METRIC_INTERVAL_MS, self._system_monitor_tick
            )
        except tk.TclError:
            self._system_metric_after_id = None

    def _start_system_monitor(self) -> None:
        if self._system_metric_after_id is not None or getattr(self, "_closing", False):
            return
        self._update_system_metrics_now()
        try:
            self._system_metric_after_id = self._schedule_after(
                self.SYSTEM_METRIC_INTERVAL_MS, self._system_monitor_tick
            )
        except tk.TclError:
            self._system_metric_after_id = None

    def _stop_system_monitor(self) -> None:
        callback = self._system_metric_after_id
        self._system_metric_after_id = None
        if callback is None:
            return
        self._cancel_after(callback)

    def _render_header_runtime_status(self) -> None:
        _ready_workers, total_workers = self._worker_counts
        ready_slots, total_slots = self._connector_counts
        self.header_runtime_label.configure(
            text=f"SLOTS {ready_slots}/{total_slots} · REGISTRY {total_workers}"
        )

    def toggle_worker_registry(self) -> None:
        """Show or hide logical scheduler registry details without changing state."""
        self._worker_registry_expanded = not self._worker_registry_expanded
        if self._worker_registry_expanded:
            self._right_stack.grid_rowconfigure(1, weight=1)
            self._worker_panel.grid_configure(sticky="nsew")
            for widget in self._worker_registry_widgets:
                widget.grid()
            self.registry_toggle_button.configure(text="Hide Registry")
            return
        for widget in self._worker_registry_widgets:
            widget.grid_remove()
        self._right_stack.grid_rowconfigure(1, weight=0)
        self._worker_panel.grid_configure(sticky="ew")
        self.registry_toggle_button.configure(text="Show Registry")

    def refresh(self) -> None:
        snapshot = self.service.snapshot()
        self.connection_label.configure(
            text="● ONLINE" if snapshot.online else "● OFFLINE",
            fg=self.theme.ready if snapshot.online else self.theme.error,
        )
        ready_workers = sum(1 for worker in snapshot.workers if worker.state is WorkerState.READY)
        total_workers = len(snapshot.workers)
        self._worker_counts = (ready_workers, total_workers)
        self.overview_projects_value.configure(text=str(len(snapshot.projects)))
        ready_slots, total_slots = self._connector_counts
        self.overview_workers_value.configure(text=f"{ready_slots} / {total_slots}")
        self.overview_connectors_value.configure(
            text=str(self._active_drift_count),
            fg=self.theme.warning if self._active_drift_count else self.theme.foreground,
        )
        self.registry_status_label.configure(
            text=f"{total_workers} registered · {ready_workers} scheduler-ready · hidden by default"
        )
        self.overview_state_value.configure(
            text="ONLINE" if snapshot.online else "OFFLINE",
            fg=self.theme.ready if snapshot.online else self.theme.error,
        )
        self._render_header_runtime_status()

        selected_project = self.selected_project_id()
        for item in self.project_list.get_children():
            self.project_list.delete(item)
        self._project_ids.clear()
        self._project_paths.clear()
        for project in snapshot.projects:
            self._project_ids.append(project.project_id)
            self._project_paths[project.project_id] = project.root_path
            self.project_list.insert(
                "",
                "end",
                iid=project.project_id,
                values=(
                    f"> {project.display_name}\n  {project.root_path}",
                    "Edit",
                ),
            )
        if not self.project_list.get_children():
            self.project_list.insert(
                "",
                "end",
                iid="__add_project__",
                values=("+ Add Project", ""),
                tags=("row-add",),
            )
        elif selected_project in self._project_ids:
            self.project_list.selection_set(selected_project)

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
                    worker.display_name,  # what the user typed, not the auto a-worker-NN id
                    worker.state.value,
                    project_name,
                    project_path,
                    connector,
                    "Edit",
                ),
                tags=(self._state_tag(worker.state),),
            )
            self._worker_ids[item] = worker.worker_id
            if selected_worker == worker.worker_id:
                self.worker_tree.selection_set(item)
                self.worker_tree.focus(item)
        if not self.worker_tree.get_children():
            self.worker_tree.insert(
                "",
                "end",
                iid="__add_worker__",
                values=("+ Add Worker", "", "", "", "", ""),
                tags=("row-add",),
            )
        self._update_lifecycle_buttons()
        self._refresh_memory_status()

    def _refresh_project_disk(self) -> None:
        """Refresh PROJECT DISK without walking the filesystem on the Tk thread."""
        disk_label = getattr(self, "overview_disk_value", None)
        if disk_label is None:
            return
        project_id = self.selected_project_id()
        if project_id is None:
            self._cancel_project_disk_scan()
            self._set_project_disk_display("—")
            return
        root_path = self._project_paths.get(project_id)
        if not root_path:
            self._cancel_project_disk_scan()
            self._set_project_disk_display("—")
            return

        normalized = os.path.normcase(os.path.abspath(root_path))
        cached = self._project_disk_cache.get(normalized)
        if cached is not None:
            if self._project_disk_request_path != normalized:
                self._cancel_project_disk_scan()
            self._project_disk_request_path = normalized
            self._set_project_disk_display(cached)
            return

        current = self._project_disk_future
        if self._project_disk_request_path == normalized and current is not None:
            # A completed Future may still be waiting for its Tk poll callback.
            # Keep the same request alive so a selection/refresh event cannot
            # cancel the just-finished result and start a duplicate scan.
            if not current.done():
                self._set_project_disk_display("…")
            return

        self._cancel_project_disk_scan()
        self._project_disk_request_id += 1
        request_id = self._project_disk_request_id
        cancel_event = Event()
        self._project_disk_cancel_event = cancel_event
        self._project_disk_request_path = normalized
        self._set_project_disk_display("…")

        from .folder_size import project_disk_display

        future = self._project_disk_executor.submit(
            project_disk_display,
            normalized,
            cancel_check=cancel_event.is_set,
        )
        self._project_disk_future = future
        self._schedule_after(
            0,
            self._poll_project_disk,
            future,
            request_id,
            normalized,
            cancel_event,
        )

    def _set_project_disk_display(self, value: str) -> None:
        disk_label = getattr(self, "overview_disk_value", None)
        if disk_label is not None:
            disk_label.configure(text=value)
        self._draw_project_disk_particles(value)

    def _draw_project_disk_particles(self, display_value: str) -> None:
        canvas = getattr(self, "_project_disk_particles", None)
        if canvas is None:
            return
        try:
            if not canvas.winfo_exists():
                return
            from .folder_size import disk_particle_levels
            levels = disk_particle_levels(display_value)
            canvas.delete("disk-particle")

            def _rgb(value: str) -> tuple[int, int, int]:
                value = value.lstrip("#")
                if len(value) != 6:
                    raise ValueError(value)
                return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4))

            low = _rgb(self.theme.muted)
            high = _rgb(self.theme.foreground)
            for index, level in enumerate(levels[:24]):
                x = 2 + index * 4
                if level <= 0:
                    fill = self.theme.border
                else:
                    rgb = tuple(
                        round(lo + (hi - lo) * max(0.0, min(1.0, level)))
                        for lo, hi in zip(low, high)
                    )
                    fill = "#{:02x}{:02x}{:02x}".format(*rgb)
                canvas.create_oval(
                    x, 6, x + 2, 8,
                    fill=fill, outline="", tags=("disk-particle",),
                )
        except (tk.TclError, ValueError):
            return

    def _cancel_project_disk_scan(self) -> None:
        cancel_event = self._project_disk_cancel_event
        if cancel_event is not None:
            cancel_event.set()
        future = self._project_disk_future
        if future is not None and not future.done():
            future.cancel()
        self._project_disk_future = None
        self._project_disk_cancel_event = None

    def _poll_project_disk(
        self,
        future: Future,
        request_id: int,
        normalized_path: str,
        cancel_event: Event,
    ) -> None:
        if self._closing:
            cancel_event.set()
            return
        if not future.done():
            self._schedule_after(
                25,
                self._poll_project_disk,
                future,
                request_id,
                normalized_path,
                cancel_event,
            )
            return

        try:
            result = future.result()
        except CancelledError:
            result = None
        except Exception:
            result = "—"

        if (
            cancel_event.is_set()
            or request_id != self._project_disk_request_id
            or normalized_path != self._project_disk_request_path
        ):
            return

        self._project_disk_future = None
        self._project_disk_cancel_event = None
        disk_label = getattr(self, "overview_disk_value", None)
        if disk_label is None:
            return
        if result is None:
            self._set_project_disk_display("—")
            return
        self._project_disk_cache[normalized_path] = result
        self._set_project_disk_display(result)

    def _refresh_memory_status(self) -> None:
        """Read-only memory-presence line for the selected project (WO-P1-057).

        Also updates the PROJECT DISK overview metric (WO-P1-070)."""
        # WO-P1-070: update disk usage from the selected project
        self._refresh_project_disk()
        label = getattr(self, "memory_status_label", None)
        if label is None:
            return
        project_id = self.selected_project_id()
        if project_id is None:
            label.configure(
                text=tr("memory.select"),
                fg=self.theme.muted,
            )
            return
        root_path = self._project_paths.get(project_id)
        if not root_path:
            label.configure(text=tr("memory.unknown"), fg=self.theme.muted)
            return
        presence = inspect_memory_presence(root_path)
        if presence.state is MemoryPresenceState.HAS_MEMORIES:
            label.configure(
                text=tr("memory.ready").format(count=presence.total_files),
                fg=self.theme.ready,
            )
        elif presence.state is MemoryPresenceState.NO_PROJECT:
            label.configure(
                text=tr("memory.path.missing"),
                fg=self.theme.error,
            )
        else:
            label.configure(
                text=tr("memory.empty"),
                fg=self.theme.warning,
            )

    def selected_project_id(self) -> str | None:
        selection = self.project_list.selection()
        if not selection:
            return None
        project_id = selection[0]
        return project_id if project_id in self._project_ids else None

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

        snapshot = self.service.snapshot()
        worker = next((row for row in snapshot.workers if row.worker_id == worker_id), None)
        project = next((row for row in snapshot.projects if row.project_id == project_id), None)
        if worker is None or project is None:
            self._handle_error("REGISTRY_NOT_FOUND")
            return

        try:
            if worker.project_id is None:
                self.service.assign_project(worker_id, project_id, mutation_allowed=True)
                action = "Assign"
            elif worker.project_id == project_id:
                self.log_activity(f"Assign       {worker_id} already uses {project_id}")
                return
            else:
                if worker.state is not WorkerState.STOPPED:
                    self._handle_error("WORKER_BUSY")
                    return
                current = worker.project_display_name or worker.project_id
                message = tr("confirm.replace.assignment").format(
                    current=current, new=project.display_name
                )
                if not self._confirm(message):
                    return
                replacer = getattr(self.service, "replace_assignment", None)
                if not callable(replacer):
                    self._handle_error("ASSIGNMENT_CONFLICT")
                    return
                replacer(worker_id, project_id, mutation_allowed=True)
                action = "Replace"
        except ControlCenterError as exc:
            self._handle_error(exc.code)
            return
        self.log_activity(f"{action:12} {worker_id} <- {project_id}")
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
            self._wiz_stitch_path.insert(0, r"C:\AI\stitch-mcp")
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
        tunnel_id = self._wiz_tunnel.get().strip()
        api_key = self._wiz_apikey.get().strip()

        local_app_data = os.environ.get("LOCALAPPDATA", "")
        base = Path(local_app_data) if local_app_data else Path.home()
        tc_config = base / "Programs" / "A-Conductor" / "dwb-serena-tunnel-starter" / "config"
        tc_config.mkdir(parents=True, exist_ok=True)

        if tunnel_id:
            (tc_config / "tunnel-id.txt").write_text(tunnel_id + "\n", encoding="utf-8")

        if api_key:
            # DPAPI-encrypt the API key (Windows CurrentUser scope) so the
            # .dpapi file is genuinely protected, matching the start.ps1 decrypt path.
            try:
                import ctypes
                import ctypes.wintypes

                class DATA_BLOB(ctypes.Structure):
                    _fields_ = [
                        ("cbData", ctypes.wintypes.DWORD),
                        ("pbData", ctypes.POINTER(ctypes.c_char)),
                    ]

                def _blob(data: bytes) -> DATA_BLOB:
                    buf = ctypes.create_string_buffer(data, len(data))
                    return DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))

                in_blob = _blob(api_key.encode("utf-8"))
                out_blob = DATA_BLOB()
                if ctypes.windll.crypt32.CryptProtectData(
                    ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob)
                ):
                    encrypted = ctypes.string_at(out_blob.pbData, out_blob.cbData)
                    ctypes.windll.kernel32.LocalFree(out_blob.pbData)
                    (tc_config / "api-key.dpapi").write_bytes(encrypted)
                else:
                    raise OSError("CryptProtectData returned false")
            except Exception:
                # Non-Windows or DPAPI unavailable: store as plain text but
                # use a non-.dpapi name so the format is honest.
                (tc_config / "api-key.txt").write_text(api_key, encoding="utf-8")

        self.log_activity("Wizard       credentials saved")
        self._wizard_advance()

    def _singleton_dialog(self, attr: str, factory):
        """Return an existing dialog (lifted to front) or create a new one.

        WO-P1-069: pressing Donate/Guide/Edit repeatedly must never stack
        duplicate windows. Store the Toplevel in ``self.<attr>``; on re-entry,
        lift + focus instead of constructing another one.
        """
        existing = getattr(self, attr, None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return existing
            except tk.TclError:
                pass
        dialog = factory()
        setattr(self, attr, dialog)
        return dialog

    def open_donate_dialog(self) -> tk.Toplevel | None:
        """Support dialog: GitHub Sponsors + PromptPay QR + TrueWallet."""
        existing = getattr(self, "_donate_dialog", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return existing
        dialog = tk.Toplevel(self.root)
        self._donate_dialog = dialog
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
        self._shutdown_ui_resources()
        self._wait_for_instance_starts()
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
            # WO-P1-068: never silently kill live chat sessions. Confirm
            # from the last known connector counts (READY per latest poll).
            running = self._connector_counts[0] if self._connector_counts else 0
            if running > 0:
                ok = self._confirm(
                    f"จะหยุดตัวเชื่อมที่กำลังรัน {running} ตัว\n"
                    "แชทที่กำลังใช้อยู่ (เช่น ChatGPT plugin) จะถูกตัดการเชื่อมต่อ\n\n"
                    "หยุดเลย หรือ ปิดโปรแกรมโดยไม่หยุด?"
                )
                if not ok:
                    self.log_activity(
                        f"Closing       skipped stop-all ({running} RUNNING kept alive)"
                    )
                    stop_all = False
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

    def _attach_row_path_tip(
        self, tree, *, column: int, label: str | Callable[[], str]
    ) -> None:
        def provider(item) -> str | None:
            return self._tree_row_path(tree, item, column=column)

        self._row_path_tip_providers[tree] = provider
        label_provider = label if callable(label) else lambda bound=label: bound
        self._row_path_menu_label_providers[tree] = label_provider
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
                label=label_provider(),
                command=lambda bound=path: self._copy_path_to_clipboard(bound),
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
            if not dialog.winfo_exists():
                return
            answer["ok"] = ok
            dialog.destroy()

        confirm_button = self._button(buttons, tr("dlg.confirm.ok"), lambda: close(True))
        confirm_button.pack(side="right", padx=(6, 0))
        cancel_button = self._button(buttons, tr("dlg.confirm.cancel"), lambda: close(False))
        cancel_button.pack(side="right")
        dialog.protocol("WM_DELETE_WINDOW", lambda: close(False))
        dialog.bind("<Escape>", lambda _event: close(False) or "break")
        dialog.bind("<Return>", lambda _event: close(True) or "break")
        dialog.grab_set()
        confirm_button.focus_set()
        dialog.wait_window()
        return answer["ok"]

    def open_add_worker_dialog(self) -> None:
        existing = getattr(self, '_add_worker_dialog', None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return existing
            except tk.TclError:
                pass

        dialog = tk.Toplevel(self.root)
        setattr(self, '_add_worker_dialog', dialog)
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
            name = name_entry.get().strip() or None
            dialog.destroy()
            self.add_worker_slot(name)

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
        self._schedule_after(0, self._poll_lifecycle_future, action, worker_id, future)

    def _poll_lifecycle_future(
        self,
        action: str,
        worker_id: str,
        future: Future,
    ) -> None:
        if not future.done():
            self._schedule_after(25, self._poll_lifecycle_future, action, worker_id, future)
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
        table = ERROR_EXPLANATIONS if get_language() == "th" else ERROR_EXPLANATIONS_EN
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

    def _restart_teaching_animation(self) -> None:
        self._stop_teaching_animation()
        self._teaching_messages = tuple(tr(f"teach.step.{index}") for index in range(1, 5))
        self._teaching_message_index = 0
        self._teaching_char_index = 0
        self._teaching_deleting = False
        self._teaching_pause_ticks = 0
        try:
            self._teaching_label.configure(text="▌")
            self._teaching_after_id = self._schedule_after(180, self._typewriter_tick)
        except tk.TclError:
            self._teaching_after_id = None

    def _stop_teaching_animation(self) -> None:
        callback = getattr(self, "_teaching_after_id", None)
        if callback is not None:
            self._cancel_after(callback)
        self._teaching_after_id = None

    def _typewriter_tick(self) -> None:
        self._teaching_after_id = None
        try:
            if not self.root.winfo_exists() or not self._teaching_label.winfo_exists():
                return
        except tk.TclError:
            return
        messages = getattr(self, "_teaching_messages", ())
        if not messages:
            return
        message = messages[self._teaching_message_index % len(messages)]
        if not self._teaching_deleting:
            if self._teaching_char_index < len(message):
                self._teaching_char_index += 1
                delay = 38
            else:
                self._teaching_pause_ticks += 1
                if self._teaching_pause_ticks >= 12:
                    self._teaching_deleting = True
                    self._teaching_pause_ticks = 0
                delay = 90
        else:
            if self._teaching_char_index > 0:
                self._teaching_char_index = max(0, self._teaching_char_index - 2)
                delay = 20
            else:
                self._teaching_deleting = False
                self._teaching_message_index = (self._teaching_message_index + 1) % len(messages)
                delay = 160
        visible = message[: self._teaching_char_index]
        try:
            self._teaching_label.configure(text=f"{visible} ▌")
            self._teaching_after_id = self._schedule_after(delay, self._typewriter_tick)
        except tk.TclError:
            self._teaching_after_id = None

    def _start_status_pulse(self) -> None:
        """Slow, gentle pulse for the ONLINE dot (minimal theme, ~1.2s cycle)."""
        self._cancel_after(self._status_pulse_after_id)
        self._status_pulse_after_id = None
        if self._closing:
            return
        self._pulse_on = not getattr(self, "_pulse_on", False)
        text = str(self.connection_label.cget("text"))
        if "ONLINE" in text:
            color = self.theme.ready if self._pulse_on else self.theme.ready_dim
            try:
                self.connection_label.configure(fg=color)
            except tk.TclError:
                return
        if self.root.winfo_exists():
            self._status_pulse_after_id = self._schedule_after(1200, self._start_status_pulse)

    def _stop_status_pulse(self) -> None:
        self._cancel_after(self._status_pulse_after_id)
        self._status_pulse_after_id = None

    def copy_text_widget_all(self, widget: tk.Text) -> str:
        text = widget.get("1.0", "end-1c")
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        return text

    def copy_text_widget_selection(self, widget: tk.Text) -> str:
        try:
            text = widget.get("sel.first", "sel.last")
        except tk.TclError:
            return ""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        return text

    def _enable_copyable_text(self, widget: tk.Text) -> None:
        def copy_selection(_event=None):
            self.copy_text_widget_selection(widget)
            return "break"

        def popup(event) -> None:
            menu = tk.Menu(widget, tearoff=0, bg=self.theme.panel, fg=self.theme.foreground)
            menu.add_command(
                label="Copy Selection",
                command=lambda: self.copy_text_widget_selection(widget),
            )
            menu.add_command(
                label="Copy All",
                command=lambda: self.copy_text_widget_all(widget),
            )
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        widget.bind("<Control-c>", copy_selection, add="+")
        widget.bind("<Control-C>", copy_selection, add="+")
        widget.bind("<Button-3>", popup, add="+")
        _attach_tip(widget, lambda: tr("tip.copy.log"), self.theme)

    def connector_help_text(self) -> str:
        return tr("tip.connector.column")

    def _align_activity_view(self) -> None:
        """Show the newest activity entries on complete text rows."""
        widget = getattr(self, "activity_text", None)
        if widget is None:
            return
        try:
            height = max(1, int(widget.winfo_height()))
            linespace = max(
                1,
                int(widget.tk.call("font", "metrics", widget.cget("font"), "-linespace")),
            )
            visible_lines = max(1, (height - 2) // linespace)
            last_line = int(widget.index("end-2c").split(".", 1)[0])
            first_line = max(1, last_line - visible_lines + 1)
            widget.yview(f"{first_line}.0")
        except (tk.TclError, ValueError):
            return

    def log_activity(self, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.activity_text.configure(state="normal")
        self.activity_text.insert("end", f"{stamp}  {text}\n")
        # Tk Text always keeps an implicit final newline.  Each log entry also
        # has its own newline, so ``see('end')`` wastes a console row on a blank
        # line and can clip the prior entry at the supported 680 px height.
        self._align_activity_view()
        self._queue_activity_alignment()
        self.activity_text.configure(state="disabled")

    def _on_palette_shortcut(self, _event=None):
        return None

    def _open_guide_web_link(self, url: str) -> None:
        candidate = str(url).strip()
        if not candidate.lower().startswith(("http://", "https://")):
            return
        self._guide_url_opener(candidate)

    def _open_guide_link(self, widget, index: str) -> None:
        for tag in widget.tag_names(index):
            if tag == "link":
                start = widget.tag_prevrange("link", index + "+1c")
                if start:
                    url = widget.get(start[0], start[1])
                    self._open_guide_web_link(url)
                    return

    def open_preferences(self) -> tk.Toplevel | None:
        """Global preferences dialog — CLI-styled switches with explanations."""
        getter = getattr(self.service, "get_preference", None)
        setter = getattr(self.service, "set_preference", None)
        if not callable(getter) or not callable(setter):
            self._handle_error("PREFERENCES_NOT_AVAILABLE")
            return None

        existing = self._preferences_window
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.deiconify()
                    existing.lift()
                    existing.focus_set()
                    return existing
            except tk.TclError:
                pass
            self._preferences_window = None

        window = tk.Toplevel(self.root)
        window.title(APP_NAME + " — " + tr("win.settings"))
        window.configure(bg=self.theme.panel)
        window.transient(self.root)
        window.resizable(True, True)
        window.minsize(560, 520)
        self._preferences_window = window
        window.bind("<Destroy>", self._on_preferences_destroy, add="+")
        frame = tk.Frame(window, bg=self.theme.panel, padx=16, pady=14)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(0, weight=1)
        self._settings_header_label = tk.Label(
            frame,
            text=tr("prefs.header"),
            bg=self.theme.panel,
            fg=self.theme.accent,
            font=(self.theme.monospace_font, 10, "bold"),
        )
        self._settings_header_label.grid(row=0, column=0, sticky="w", pady=(0, 10))

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
            text=tr("prefs.supervised"),
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
        self._supervised_checkbox = checkbox
        checkbox.grid(row=2, column=0, sticky="w")
        _attach_tip(
            checkbox,
            lambda: tr("prefs.supervised.help"),
            self.theme,
        )
        self._supervised_summary_label = tk.Label(
            frame,
            text=tr("prefs.supervised.summary"),
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 8),
            anchor="w",
            wraplength=460,
            justify="left",
        )
        self._supervised_summary_label.grid(row=3, column=0, sticky="w", pady=(2, 8))

        language_display = {"th": "Thai", "zh-CN": "中文", "en": "English"}
        language_var = tk.StringVar(value=language_display.get(get_language(), "Thai"))

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
        self._shutdown_checkbox = shutdown_box
        shutdown_box.grid(row=1, column=0, sticky="w", pady=(0, 2))
        _attach_tip(shutdown_box, lambda: tr("prefs.shutdown.help"), self.theme)

        language_row = tk.Frame(frame, bg=self.theme.panel)
        language_row.grid(row=4, column=0, sticky="ew", pady=(2, 0))
        self._language_label = tk.Label(
            language_row, text=tr("prefs.language"), bg=self.theme.panel,
            fg=self.theme.foreground, font=(self.theme.monospace_font, 9),
        )
        self._language_label.pack(side="left", padx=(0, 8))
        self._language_combo = ttk.Combobox(
            language_row, textvariable=language_var, values=("Thai", "中文", "English"),
            state="readonly", width=12,
        )
        self._language_combo.pack(side="left")
        self._language_combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self._save_language_preference(setter, language_var),
        )
        _attach_tip(self._language_combo, lambda: tr("prefs.language.help"), self.theme)
        self._language_status_label = tk.Label(
            frame, text=tr("prefs.language.restart"), bg=self.theme.panel, fg=self.theme.muted,
            font=(self.theme.monospace_font, 8), anchor="w", wraplength=460, justify="left",
        )
        self._language_status_label.grid(row=5, column=0, sticky="w", pady=(2, 8))

        models_frame = tk.Frame(frame, bg=self.theme.background, highlightthickness=1, highlightbackground=self.theme.border, padx=10, pady=8)
        models_frame.grid(row=6, column=0, sticky="nsew", pady=(6, 10))
        models_frame.grid_columnconfigure(0, weight=1)
        self._models_agents_header_label = tk.Label(models_frame, text=tr("prefs.models_agents.header"), bg=self.theme.background, fg=self.theme.accent, font=(self.theme.monospace_font, 9, "bold"), anchor="w")
        self._models_agents_header_label.grid(row=0, column=0, sticky="w")
        self._models_agents_refresh_button = self._button(models_frame, "Refresh", self._refresh_models_agents_panel)
        self._models_agents_refresh_button.grid(row=0, column=1, sticky="e", padx=(8, 0))
        actions = tk.Frame(models_frame, bg=self.theme.background)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(7, 2))
        actions.grid_columnconfigure(0, weight=1)
        self._models_agents_provider_combo = ttk.Combobox(actions, state="readonly", width=42, takefocus=True)
        self._models_agents_provider_combo.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._models_agents_provider_combo.bind("<<ComboboxSelected>>", lambda _event: self._sync_models_agents_action_controls())
        self._models_agents_edit_button = self._button(actions, tr("prefs.models_agents.edit"), self._open_selected_provider_edit_dialog)
        self._models_agents_edit_button.grid(row=0, column=1, padx=(0, 4))
        _attach_tip(self._models_agents_edit_button, lambda: tr("prefs.models_agents.edit.help"), self.theme)
        self._models_agents_toggle_button = self._button(actions, tr("prefs.models_agents.disable"), self._toggle_selected_provider)
        self._models_agents_toggle_button.grid(row=0, column=2, padx=(0, 4))
        _attach_tip(self._models_agents_toggle_button, lambda: tr("prefs.models_agents.toggle.help"), self.theme)
        self._models_agents_test_button = self._button(actions, tr("prefs.models_agents.test"), self._test_selected_provider)
        self._models_agents_test_button.grid(row=0, column=3)
        _attach_tip(self._models_agents_test_button, lambda: tr("prefs.models_agents.test.help"), self.theme)
        self._models_agents_action_label = tk.Label(actions, text="", bg=self.theme.background, fg=self.theme.muted, font=(self.theme.monospace_font, 8), anchor="w")
        self._models_agents_action_label.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(3, 0))
        self._models_agents_evidence_button = self._button(actions, tr("prefs.models_agents.evidence"), self._open_selected_provider_evidence)
        self._models_agents_evidence_button.grid(row=1, column=3, sticky="e", pady=(3, 0))
        _attach_tip(self._models_agents_evidence_button, lambda: tr("prefs.models_agents.evidence.help"), self.theme)
        self._models_agents_text = tk.Text(models_frame, height=10, width=72, bg=self.theme.background, fg=self.theme.foreground, insertbackground=self.theme.accent, wrap="word", borderwidth=0, highlightthickness=0, font=(self.theme.monospace_font, 8), padx=0, pady=6, takefocus=True)
        self._models_agents_text.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self._models_agents_text.configure(state="disabled")
        self._models_agents_last_rows = ()
        self._models_agents_last_error = None
        self._models_agents_loading = True
        self._render_models_agents_panel()
        self._refresh_models_agents_panel()
        self._button(frame, tr("btn.close"), lambda: window.destroy() if window.winfo_exists() else None).grid(row=7, column=0, sticky="w")
        return window

    @staticmethod
    def _models_agents_enum_text(value) -> str:
        return "-" if value is None else str(getattr(value, "value", value))

    @staticmethod
    def _models_agents_error_code(exc: Exception) -> str:
        code = getattr(exc, "code", None)
        allowed = {"PROVIDER_STORE_NOT_AVAILABLE", "CONFIG_STORE_UNAVAILABLE", "CONFIG_STORE_SCHEMA_UNAVAILABLE", "CONFIG_STORE_READ_FAILED", "PROVIDER_CONFIGURATION_CORRUPT"}
        return code if isinstance(code, str) and code in allowed else "PROVIDER_READ_FAILED"

    @staticmethod
    def _models_agents_action_error_code(exc: Exception) -> str:
        code = getattr(exc, "code", None)
        allowed = {
            "PROVIDER_STORE_NOT_AVAILABLE",
            "CONFIG_STORE_UNAVAILABLE",
            "PROVIDER_GENERATION_STALE",
            "PROVIDER_GENERATION_EXPECTED",
            "PROVIDER_GENERATION_EXHAUSTED",
            "PROVIDER_CONFIGURATION_IN_USE",
            "PROVIDER_PROFILE_INVALID",
            "PROVIDER_TEST_TARGET_UNAVAILABLE",
            "PROVIDER_OBSERVATION_GENERATION_STALE",
            "PROVIDER_CONFIGURATION_CORRUPT",
            "CONFIG_STORE_SCHEMA_UNAVAILABLE",
            "CONFIG_STORE_READ_FAILED",
        }
        return code if isinstance(code, str) and code in allowed else "PROVIDER_ACTION_FAILED"

    def _selected_models_agents_row(self):
        combo = getattr(self, "_models_agents_provider_combo", None)
        if combo is None:
            return None
        try:
            index = combo.current()
        except tk.TclError:
            return None
        if index < 0 or index >= len(self._models_agents_last_rows):
            return None
        return self._models_agents_last_rows[index]

    def _sync_models_agents_action_controls(self) -> None:
        combo = getattr(self, "_models_agents_provider_combo", None)
        if combo is None:
            return
        try:
            previous_id = None
            previous_index = combo.current()
            if 0 <= previous_index < len(self._models_agents_provider_ids):
                previous_id = self._models_agents_provider_ids[previous_index]
            rows = () if self._models_agents_loading or self._models_agents_last_error else self._models_agents_last_rows
            ids = tuple(str(getattr(row, "provider_id", "")) for row in rows)
            labels = tuple(
                f"{getattr(row, 'display_name', provider_id)} [{provider_id}]"
                for row, provider_id in zip(rows, ids)
            )
            self._models_agents_provider_ids = ids
            combo.configure(values=labels)
            if ids:
                combo.current(ids.index(previous_id) if previous_id in ids else 0)
            else:
                combo.set("")
            busy = self._models_agents_action_pending_provider is not None
            usable = bool(ids) and not busy
            combo.configure(state="readonly" if usable else "disabled")
            for name in ("_models_agents_edit_button", "_models_agents_toggle_button", "_models_agents_test_button", "_models_agents_evidence_button"):
                button = getattr(self, name, None)
                if button is not None:
                    button.configure(state="normal" if usable else "disabled")
            row = self._selected_models_agents_row() if ids else None
            toggle = getattr(self, "_models_agents_toggle_button", None)
            if toggle is not None:
                toggle.configure(
                    text=tr("prefs.models_agents.disable")
                    if row is None or bool(getattr(row, "enabled", False))
                    else tr("prefs.models_agents.enable")
                )
            label = getattr(self, "_models_agents_action_label", None)
            if label is not None:
                label.configure(text=self._models_agents_action_message)
            # provider switch discards any pending evidence fetch for the old provider
            if self._provider_evidence_pending:
                current_row = self._selected_models_agents_row() if ids else None
                current_id = None if current_row is None else str(getattr(current_row, "provider_id", ""))
                if (
                    current_id is not None
                    and self._provider_evidence_provider_id is not None
                    and current_id != self._provider_evidence_provider_id
                ):
                    self._invalidate_provider_evidence()
                    self._render_provider_evidence_text(loading=True)
        except tk.TclError:
            return

    def _submit_models_agents_action(self, provider_id: str, action: str, fn, /, *args, **kwargs) -> None:
        if not self._models_agents_window_alive() or self._models_agents_action_pending_provider is not None:
            return
        self._models_agents_action_request_id += 1
        request_id = self._models_agents_action_request_id
        self._models_agents_action_pending_provider = provider_id
        self._models_agents_action_message = f"{action.upper()}: RUNNING"
        self._sync_models_agents_action_controls()
        try:
            future = self._background_executor.submit(fn, *args, **kwargs)
        except Exception as exc:
            self._models_agents_action_pending_provider = None
            code = self._models_agents_action_error_code(exc)
            self._models_agents_action_message = code
            self._sync_models_agents_action_controls()
            self._handle_error(code)
            return
        self._models_agents_action_future = future
        self._schedule_after(0, self._poll_models_agents_action_future, request_id, provider_id, action, future)

    def _poll_models_agents_action_future(self, request_id: int, provider_id: str, action: str, future: Future) -> None:
        if request_id != self._models_agents_action_request_id:
            return
        if not future.done():
            self._schedule_after(25, self._poll_models_agents_action_future, request_id, provider_id, action, future)
            return
        self._models_agents_action_future = None
        self._models_agents_action_pending_provider = None
        if not self._models_agents_window_alive():
            return
        action_succeeded = False
        try:
            result = future.result()
            action_succeeded = True
            if action == "test":
                provenance = getattr(result, "provenance", None)
                if provenance == "zai-quota-monitor:unsupported-route":
                    self._models_agents_action_message = "TEST: UNSUPPORTED"
                else:
                    health = self._models_agents_enum_text(getattr(result, "health", None))
                    self._models_agents_action_message = f"TEST: {health}"
            elif action == "edit-unsupported-credential":
                self._models_agents_action_message = (
                    "EDIT: SAVED [PROVIDER_CREDENTIAL_REF_UNSUPPORTED_RUNTIME] — "
                    + tr("prefs.models_agents.unsupported_credential")
                )
            else:
                self._models_agents_action_message = f"{action.upper()}: SAVED generation={result}"
        except Exception as exc:
            code = self._models_agents_action_error_code(exc)
            self._models_agents_action_message = code
            self._handle_error(code)
        self._sync_models_agents_action_controls()
        if action_succeeded:
            self._refresh_open_provider_evidence(provider_id)
        self._refresh_models_agents_panel()

    def _refresh_open_provider_evidence(self, provider_id: str) -> None:
        if (
            not self._provider_evidence_window_alive()
            or self._provider_evidence_provider_id != provider_id
        ):
            return
        fetcher = getattr(self.service, "provider_selection_evidence", None)
        if not callable(fetcher):
            return
        self._invalidate_provider_evidence()
        self._render_provider_evidence_text(loading=True)
        self._submit_provider_evidence_fetch(provider_id, fetcher)

    def _models_agents_window_alive(self) -> bool:
        window = self._preferences_window
        if window is None:
            return False
        try:
            return bool(window.winfo_exists())
        except tk.TclError:
            return False

    def _open_selected_provider_edit_dialog(self):
        existing = getattr(self, "_provider_edit_window", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return existing
            except tk.TclError:
                pass
        row = self._selected_models_agents_row()
        if row is None:
            return None
        provider_id = str(getattr(row, "provider_id", ""))
        generation = getattr(row, "configuration_generation", None)
        if not provider_id or generation is None:
            self._models_agents_action_message = "PROVIDER_GENERATION_STALE"
            self._sync_models_agents_action_controls()
            return None
        updater = getattr(self.service, "update_provider_profile", None)
        if not callable(updater):
            self._models_agents_action_message = "PROVIDER_STORE_NOT_AVAILABLE"
            self._sync_models_agents_action_controls()
            return None
        from .provider_configuration import EgressBoundary, ProviderTrustClass

        parent = self._preferences_window or self.root
        dialog = tk.Toplevel(parent)
        self._provider_edit_window = dialog
        dialog.title(f"Edit Provider — {provider_id}")
        dialog.configure(bg=self.theme.panel)
        dialog.resizable(False, False)
        body = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=12)
        body.grid(row=0, column=0, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)
        display_var = tk.StringVar(dialog, value=str(getattr(row, "display_name", "")))
        type_var = tk.StringVar(dialog, value=str(getattr(row, "provider_type", "")))
        trust_var = tk.StringVar(dialog, value=self._models_agents_enum_text(getattr(row, "trust_class", None)))
        egress_var = tk.StringVar(dialog, value=self._models_agents_enum_text(getattr(row, "egress_boundary", None)))
        concurrency_var = tk.StringVar(dialog, value=str(getattr(row, "max_concurrency", 1)))
        credential_var = tk.StringVar(dialog, value="")
        fields = (("Provider", provider_id), ("Display name", display_var), ("Provider type", type_var))
        for index, (label_text, value) in enumerate(fields):
            tk.Label(body, text=label_text, bg=self.theme.panel, fg=self.theme.muted, font=(self.theme.monospace_font, 8), anchor="w").grid(row=index, column=0, sticky="w", padx=(0, 8), pady=3)
            if isinstance(value, tk.StringVar):
                tk.Entry(body, textvariable=value, width=42).grid(row=index, column=1, sticky="ew", pady=3)
            else:
                tk.Label(body, text=value, bg=self.theme.panel, fg=self.theme.foreground, font=(self.theme.monospace_font, 8), anchor="w").grid(row=index, column=1, sticky="w", pady=3)
        tk.Label(body, text="Trust", bg=self.theme.panel, fg=self.theme.muted, font=(self.theme.monospace_font, 8)).grid(row=3, column=0, sticky="w", pady=3)
        ttk.Combobox(body, textvariable=trust_var, state="readonly", values=tuple(item.value for item in ProviderTrustClass), width=39).grid(row=3, column=1, sticky="ew", pady=3)
        tk.Label(body, text="Egress", bg=self.theme.panel, fg=self.theme.muted, font=(self.theme.monospace_font, 8)).grid(row=4, column=0, sticky="w", pady=3)
        ttk.Combobox(body, textvariable=egress_var, state="readonly", values=tuple(item.value for item in EgressBoundary), width=39).grid(row=4, column=1, sticky="ew", pady=3)
        tk.Label(body, text="Max concurrency", bg=self.theme.panel, fg=self.theme.muted, font=(self.theme.monospace_font, 8)).grid(row=5, column=0, sticky="w", pady=3)
        tk.Entry(body, textvariable=concurrency_var, width=42).grid(row=5, column=1, sticky="ew", pady=3)
        tk.Label(body, text=tr("prefs.models_agents.credential.label"), bg=self.theme.panel, fg=self.theme.muted, font=(self.theme.monospace_font, 8)).grid(row=6, column=0, sticky="w", pady=3)
        tk.Entry(body, textvariable=credential_var, width=42, show="").grid(row=6, column=1, sticky="ew", pady=3)
        tk.Label(body, text=tr("prefs.models_agents.credential.help"), bg=self.theme.panel, fg=self.theme.muted, font=(self.theme.monospace_font, 7), wraplength=420, justify="left").grid(row=7, column=0, columnspan=2, sticky="w", pady=(1, 7))

        def close_dialog() -> None:
            try:
                if dialog.winfo_exists():
                    dialog.destroy()
            except tk.TclError:
                pass

        def submit() -> None:
            try:
                max_concurrency = int(concurrency_var.get().strip())
            except ValueError:
                self._models_agents_action_message = "PROVIDER_PROFILE_INVALID"
                self._sync_models_agents_action_controls()
                self._handle_error("PROVIDER_PROFILE_INVALID")
                return
            credential_ref = credential_var.get().strip()
            kwargs = dict(
                expected_generation=generation,
                display_name=display_var.get().strip(),
                provider_type=type_var.get().strip(),
                trust_class=trust_var.get(),
                egress_boundary=egress_var.get(),
                max_concurrency=max_concurrency,
            )
            action = "edit"
            if credential_ref:
                kwargs["credential_ref"] = credential_ref
                support_checker = getattr(
                    self.service, "provider_credential_ref_runtime_supported", None
                )
                if not callable(support_checker) or not support_checker(credential_ref):
                    action = "edit-unsupported-credential"
            close_dialog()
            self._submit_models_agents_action(provider_id, action, updater, provider_id, **kwargs)

        self._button(body, tr("prefs.models_agents.save"), submit).grid(row=8, column=0, sticky="w", pady=(4, 0))
        self._button(body, tr("prefs.models_agents.cancel"), close_dialog).grid(row=8, column=1, sticky="e", pady=(4, 0))
        dialog.bind("<Destroy>", lambda event: setattr(self, "_provider_edit_window", None) if event.widget is dialog else None, add="+")
        return dialog

    def _toggle_selected_provider(self) -> None:
        row = self._selected_models_agents_row()
        if row is None:
            return
        setter = getattr(self.service, "set_provider_enabled", None)
        generation = getattr(row, "configuration_generation", None)
        provider_id = str(getattr(row, "provider_id", ""))
        if not callable(setter) or generation is None or not provider_id:
            self._models_agents_action_message = "PROVIDER_STORE_NOT_AVAILABLE" if not callable(setter) else "PROVIDER_GENERATION_STALE"
            self._sync_models_agents_action_controls()
            return
        enabled = not bool(getattr(row, "enabled", False))
        self._submit_models_agents_action(
            provider_id,
            "enable" if enabled else "disable",
            setter,
            provider_id,
            enabled=enabled,
            expected_generation=generation,
        )

    def _test_selected_provider(self) -> None:
        row = self._selected_models_agents_row()
        if row is None:
            return
        tester = getattr(self.service, "test_provider", None)
        provider_id = str(getattr(row, "provider_id", ""))
        if not callable(tester) or not provider_id:
            self._models_agents_action_message = "PROVIDER_STORE_NOT_AVAILABLE"
            self._sync_models_agents_action_controls()
            return
        self._submit_models_agents_action(provider_id, "test", tester, provider_id)

    @staticmethod
    def _provider_evidence_error_code(exc: Exception) -> str:
        code = getattr(exc, "code", None)
        allowed = {
            "PROVIDER_STORE_NOT_AVAILABLE",
            "CONFIG_STORE_UNAVAILABLE",
            "CONFIG_STORE_SCHEMA_UNAVAILABLE",
            "CONFIG_STORE_READ_FAILED",
            "PROVIDER_CONFIGURATION_CORRUPT",
            "PROVIDER_ADMISSION_RECORD_INVALID",
            "PROVIDER_GENERATION_INVALID",
            "PROVIDER_EVIDENCE_TARGET_UNAVAILABLE",
            "PROVIDER_ADMISSION_LIST_LIMIT_INVALID",
            "PROVIDER_ADMISSION_FILTER_INVALID",
        }
        return code if isinstance(code, str) and code in allowed else "PROVIDER_ACTION_FAILED"

    def _provider_evidence_window_alive(self) -> bool:
        window = self._provider_evidence_window
        if window is None:
            return False
        try:
            return bool(window.winfo_exists())
        except tk.TclError:
            return False

    def _invalidate_provider_evidence(self) -> None:
        self._provider_evidence_request_id += 1
        self._provider_evidence_pending = False
        self._provider_evidence_future = None
        self._provider_evidence_cache = None

    def _provider_evidence_graph_context(self) -> tuple[str | None, str | None]:
        return (
            getattr(self, "_graph_monitor_graph_id", None),
            getattr(self, "_graph_monitor_run_id", None),
        )

    def _invalidate_provider_evidence_graph_links(self) -> None:
        cache = getattr(self, "_provider_evidence_cache", None)
        if cache is None:
            return
        provider_id, row, evidence, _links, _graph_context = cache
        self._provider_evidence_cache = (provider_id, row, evidence, {}, (None, None))
        self._render_provider_evidence_from_cache()

    def _open_selected_provider_evidence(self):
        row = self._selected_models_agents_row()
        if row is None:
            return None
        provider_id = str(getattr(row, "provider_id", ""))
        fetcher = getattr(self.service, "provider_selection_evidence", None)
        if not provider_id or not callable(fetcher):
            self._models_agents_action_message = "PROVIDER_STORE_NOT_AVAILABLE"
            self._sync_models_agents_action_controls()
            return None
        if self._provider_evidence_pending:
            return self._provider_evidence_window  # single-flight: coalesce

        dialog = self._provider_evidence_window
        if dialog is None or not self._provider_evidence_window_alive():
            parent = self._preferences_window or self.root
            dialog = tk.Toplevel(parent)
            dialog.configure(bg=self.theme.panel)
            body = tk.Frame(dialog, bg=self.theme.panel, padx=12, pady=10)
            body.pack(fill="both", expand=True)
            self._provider_evidence_text = tk.Text(
                body, height=18, width=78, bg=self.theme.background,
                fg=self.theme.foreground, insertbackground=self.theme.accent,
                wrap="word", borderwidth=0, highlightthickness=0,
                font=(self.theme.monospace_font, 8), padx=8, pady=6, takefocus=True,
            )
            self._provider_evidence_text.pack(fill="both", expand=True)
            self._provider_evidence_text.configure(state="disabled")
            self._enable_copyable_text(self._provider_evidence_text)
            self._provider_evidence_window = dialog

            def _on_evidence_destroy(event) -> None:
                if event.widget is dialog:
                    self._provider_evidence_window = None
                    self._provider_evidence_provider_id = None
                    self._invalidate_provider_evidence()

            dialog.bind("<Destroy>", _on_evidence_destroy, add="+")
        self._provider_evidence_provider_id = provider_id
        dialog.title(f"Evidence - {provider_id}")
        self._render_provider_evidence_text(loading=True)
        self._submit_provider_evidence_fetch(provider_id, fetcher)
        return dialog

    def _submit_provider_evidence_fetch(self, provider_id: str, fetcher) -> None:
        self._provider_evidence_request_id += 1
        request_id = self._provider_evidence_request_id
        self._provider_evidence_pending = True
        self._provider_evidence_cache = None
        graph_context = self._provider_evidence_graph_context()

        def _work():
            row, evidence = fetcher(provider_id, admissions_limit=10)
            links = self._read_provider_graph_links(*graph_context)
            return row, evidence, links, graph_context

        try:
            future = self._background_executor.submit(_work)
        except Exception as exc:
            self._provider_evidence_pending = False
            code = self._provider_evidence_error_code(exc)
            self._render_provider_evidence_text(error_code=code)
            self._handle_error(code)
            return
        self._provider_evidence_future = future
        self._schedule_after(0, self._poll_provider_evidence_future, request_id, provider_id, future)

    def _poll_provider_evidence_future(self, request_id: int, provider_id: str, future: Future) -> None:
        if request_id != self._provider_evidence_request_id:
            return
        if not future.done():
            self._schedule_after(25, self._poll_provider_evidence_future, request_id, provider_id, future)
            return
        self._provider_evidence_future = None
        self._provider_evidence_pending = False
        if not self._provider_evidence_window_alive():
            return
        try:
            row, evidence, links, graph_context = future.result()
            if graph_context != self._provider_evidence_graph_context():
                links = {}
                graph_context = (None, None)
            self._provider_evidence_cache = (provider_id, row, evidence, links, graph_context)
        except Exception as exc:
            code = self._provider_evidence_error_code(exc)
            self._provider_evidence_cache = None
            self._render_provider_evidence_text(error_code=code)
            self._handle_error(code)
            return
        self._render_provider_evidence_from_cache()

    def _read_provider_graph_links(
        self, graph_id: str | None, run_id: str | None
    ) -> dict[str, str]:
        """Background-thread read pinned to the submit-time explicit graph context."""
        if not graph_id or not run_id:
            return {}
        snapshot_fn = getattr(self.service, "operator_graph_snapshot", None)
        if not callable(snapshot_fn):
            return {}
        try:
            snapshot = snapshot_fn(graph_id, run_id, event_limit=1)
        except Exception:
            return {}
        return provider_graph_evidence_links(snapshot, graph_id, run_id)

    def _format_provider_evidence(self, provider_id, row, evidence, links, graph_context) -> str:
        from datetime import timezone as _tz

        def _iso(value):
            if value is None:
                return "-"
            try:
                return value.astimezone(_tz.utc).isoformat().replace("+00:00", "Z")
            except (AttributeError, ValueError, OSError):
                return str(value)

        lines = [f"PROVIDER EVIDENCE - {getattr(row, 'display_name', provider_id)} [{provider_id}]"]
        lines.append("SELECTION_REASON=UNKNOWN    FALLBACK_REASON=NOT_EVALUATED")
        lines.append("")
        lines.append(tr("prefs.models_agents.evidence.admissions").upper())
        for index, item in enumerate(evidence.admissions, start=1):
            node_id = links.get(item.execution_id)
            lines.append(
                f"[{index}] {item.admission_id} status={item.status} "
                f"generation={item.generation_relation} expiry={item.expiry_observation}"
            )
            lines.append(f"    execution_id={item.execution_id} batch_id={item.batch_id}")
            lines.append(
                f"    acquired={_iso(item.acquired_at)} expires={_iso(item.expires_at)} "
                f"released={_iso(item.released_at)} reconciled={_iso(item.reconciled_at)}"
            )
            lines.append(f"    graph={node_id if node_id else 'NO_READABLE_GRAPH_EVIDENCE'}")
        lines.append("")
        lines.append(tr("prefs.models_agents.evidence.current").upper())
        lines.append(
            f"  {getattr(row, 'display_name', provider_id)}  "
            f"[{'ENABLED' if getattr(row, 'enabled', False) else 'DISABLED'} | "
            f"{'CONFIGURED' if getattr(row, 'configured', False) else 'NOT CONFIGURED'} | "
            f"{'READY' if getattr(row, 'runtime_ready', False) else 'NOT READY'} | "
            f"AUTH={getattr(row, 'task_authorization', 'NOT_EVALUATED')}]"
        )
        lines.append(
            f"  reason={getattr(row, 'readiness_reason', 'UNKNOWN')} "
            f"health={self._models_agents_enum_text(getattr(row, 'health', None))} "
            f"generation={getattr(row, 'configuration_generation', '-')}"
        )
        models = ", ".join(str(getattr(m, "model_id", m)) for m in getattr(row, "models", ())) or "-"
        harnesses = ", ".join(self._models_agents_enum_text(h) for h in getattr(row, "harness_strategies", ())) or "-"
        lines.append(f"  {tr('prefs.models_agents.evidence.declared')}: models={models} harness={harnesses}")
        graph_id, run_id = graph_context
        if links and graph_id and run_id:
            lines.append(f"  graph_context={graph_id} run={run_id}")
        return "\n".join(lines)

    def _render_provider_evidence_text(self, *, loading: bool = False, error_code: str | None = None) -> None:
        widget = getattr(self, "_provider_evidence_text", None)
        if widget is None:
            return
        try:
            if not widget.winfo_exists():
                return
            if loading:
                content = tr("prefs.models_agents.evidence.loading")
            elif error_code is not None:
                content = f"{tr('prefs.models_agents.evidence.error')} [{error_code}]"
            else:
                content = ""
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", content)
            widget.configure(state="disabled")
        except tk.TclError:
            return

    def _render_provider_evidence_from_cache(self) -> None:
        cache = self._provider_evidence_cache
        if cache is None:
            return
        widget = getattr(self, "_provider_evidence_text", None)
        if widget is None or not self._provider_evidence_window_alive():
            return
        provider_id, row, evidence, links, graph_context = cache
        try:
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", self._format_provider_evidence(provider_id, row, evidence, links, graph_context))
            widget.configure(state="disabled")
        except tk.TclError:
            return

    def _format_models_agents_row(self, row) -> str:
        configured = "CONFIGURED" if bool(getattr(row, "configured", False)) else "NOT CONFIGURED"
        ready = "READY" if bool(getattr(row, "runtime_ready", False)) else "NOT READY"
        enabled = "ENABLED" if bool(getattr(row, "enabled", False)) else "DISABLED"
        trust = self._models_agents_enum_text(getattr(row, "trust_class", None))
        egress = self._models_agents_enum_text(getattr(row, "egress_boundary", None))
        health = self._models_agents_enum_text(getattr(row, "health", None))
        reason = str(getattr(row, "readiness_reason", "UNKNOWN"))
        authorization = str(getattr(row, "task_authorization", "NOT_EVALUATED"))
        generation = getattr(row, "configuration_generation", None)
        provenance = getattr(row, "provenance", None) or "-"
        age = getattr(row, "observation_age_seconds", None)
        age_text = "-" if age is None else f"{float(age):.1f}s"
        models = ", ".join(str(getattr(item, "model_id", item)) for item in getattr(row, "models", ())) or "-"
        harnesses = ", ".join(self._models_agents_enum_text(item) for item in getattr(row, "harness_strategies", ())) or "-"
        quota = getattr(row, "quota", None)
        if quota is None:
            quota_text = "-"
        else:
            remaining = getattr(quota, "remaining", None)
            reset_in = getattr(quota, "reset_in_seconds", None)
            reset_at = getattr(quota, "reset_at", None)
            reset = f"{reset_in}s" if reset_in is not None else (str(reset_at) if reset_at is not None else "-")
            quota_text = f"remaining={remaining if remaining is not None else '-'} reset={reset}"
        return (f"{getattr(row, 'display_name', getattr(row, 'provider_id', 'Provider'))}  [{enabled} | {configured} | {ready} | AUTH={authorization}]\n"
                f"  reason={reason} health={health} trust={trust} egress={egress} generation={generation if generation is not None else '-'}\n"
                f"  models={models} harness={harnesses} quota={quota_text} provenance={provenance} age={age_text}")

    def _render_models_agents_panel(self) -> None:
        widget = getattr(self, "_models_agents_text", None)
        if widget is None:
            return
        try:
            if not widget.winfo_exists():
                return
            if self._models_agents_loading:
                content = tr("prefs.models_agents.loading")
            elif self._models_agents_last_error is not None:
                content = f"{tr('prefs.models_agents.error')} [{self._models_agents_last_error}]"
            elif not self._models_agents_last_rows:
                content = tr("prefs.models_agents.empty")
            else:
                content = "\n\n".join(self._format_models_agents_row(row) for row in self._models_agents_last_rows)
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", content)
            widget.configure(state="disabled")
            self._sync_models_agents_action_controls()
        except tk.TclError:
            return

    def _refresh_models_agents_panel(self) -> None:
        if not self._models_agents_window_alive() or self._models_agents_refresh_pending:
            return
        fetcher = getattr(self.service, "provider_operator_rows", None)
        self._models_agents_request_id += 1
        request_id = self._models_agents_request_id
        self._models_agents_refresh_pending = True
        self._models_agents_loading = True
        self._models_agents_last_error = None
        self._render_models_agents_panel()
        if not callable(fetcher):
            self._models_agents_refresh_pending = False
            self._models_agents_loading = False
            self._models_agents_last_error = "PROVIDER_STORE_NOT_AVAILABLE"
            self._render_models_agents_panel()
            return
        try:
            future = self._background_executor.submit(fetcher)
        except Exception as exc:
            self._models_agents_refresh_pending = False
            self._models_agents_loading = False
            self._models_agents_last_error = self._models_agents_error_code(exc)
            self._render_models_agents_panel()
            return
        self._models_agents_future = future
        self._schedule_after(0, self._poll_models_agents_future, request_id, future)

    def _poll_models_agents_future(self, request_id: int, future: Future) -> None:
        if request_id != self._models_agents_request_id:
            return
        if not future.done():
            self._schedule_after(25, self._poll_models_agents_future, request_id, future)
            return
        self._models_agents_refresh_pending = False
        self._models_agents_future = None
        self._models_agents_loading = False
        if not self._models_agents_window_alive():
            return
        try:
            self._models_agents_last_rows = tuple(future.result())
            self._models_agents_last_error = None
        except Exception as exc:
            self._models_agents_last_rows = ()
            self._models_agents_last_error = self._models_agents_error_code(exc)
        self._render_models_agents_panel()

    def _on_preferences_destroy(self, event) -> None:
        if event.widget is self._preferences_window:
            self._preferences_window = None
            self._models_agents_request_id += 1
            self._models_agents_refresh_pending = False
            self._models_agents_future = None
            self._models_agents_loading = False
            self._models_agents_action_request_id += 1
            self._models_agents_action_future = None
            self._models_agents_action_pending_provider = None
            self._provider_edit_window = None
            evidence_window = self._provider_evidence_window
            self._provider_evidence_window = None
            self._provider_evidence_provider_id = None
            self._invalidate_provider_evidence()
            if evidence_window is not None:
                try:
                    if evidence_window.winfo_exists():
                        evidence_window.destroy()
                except tk.TclError:
                    pass

    def _save_shutdown_preference(self, setter, var: tk.BooleanVar) -> None:
        try:
            setter("shutdown_stops_instances", var.get())
        except Exception:
            self._handle_error("PREFERENCE_SAVE_FAILED")
            return
        self.log_activity(f"Settings     shutdown_stops={'ON' if var.get() else 'OFF'}")

    def _save_language_preference(self, setter, var: tk.StringVar) -> None:
        display_to_code = {"Thai": "th", "中文": "zh-CN", "English": "en"}
        code = display_to_code.get(str(var.get()), "th")
        try:
            setter("language_zh", code == "zh-CN")
            setter("language", code == "en")
        except Exception:
            self._handle_error("PREFERENCE_SAVE_FAILED")
            return
        set_language(code)
        self._refresh_language_surfaces()
        self._restart_teaching_animation()
        self.log_activity(f"Settings     language={code}")

    def _refresh_language_surfaces(self) -> None:
        window = getattr(self, "_preferences_window", None)
        if window is not None:
            try:
                if window.winfo_exists():
                    window.title(APP_NAME + " — " + tr("win.settings"))
                    self._settings_header_label.configure(text=tr("prefs.header"))
                    self._supervised_checkbox.configure(text=tr("prefs.supervised"))
                    self._supervised_summary_label.configure(
                        text=tr("prefs.supervised.summary")
                    )
                    self._shutdown_checkbox.configure(text=tr("prefs.shutdown"))
                    self._language_label.configure(text=tr("prefs.language"))
                    self._language_status_label.configure(text=tr("prefs.language.restart"))
                    header = getattr(self, "_models_agents_header_label", None)
                    if header is not None:
                        header.configure(text=tr("prefs.models_agents.header"))
                    self._render_models_agents_panel()
                    self._render_provider_evidence_from_cache()
            except tk.TclError:
                pass
        self._refresh_memory_status()
        self._update_monitor_now()

    def _save_supervised_preference(self, setter, var: tk.BooleanVar) -> None:
        try:
            setter("supervised", var.get())
        except Exception:
            self._handle_error("PREFERENCE_SAVE_FAILED")
            return
        self.log_activity(f"Settings     supervised={'ON' if var.get() else 'OFF'}")

    def open_guide(self) -> tk.Toplevel | None:
        path = find_user_guide_path()
        if path is None:
            self._handle_error("GUIDE_NOT_FOUND")
            return None
        try:
            if self._guide_opener is not None:
                self._guide_opener(path)
                self.log_activity("Guide        opened external")
                return None
            window = self._show_guide_window(path)
            self.log_activity("Guide        opened")
            return window
        except Exception:
            self._handle_error("GUIDE_OPEN_FAILED")
            return None

    def _show_guide_markdown_fallback(self, parent, content: str) -> tk.Text:
        """Render the legacy read-only Markdown view when rich HTML is unavailable."""
        text = tk.Text(
            parent,
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
        scroll = ttk.Scrollbar(parent, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.insert("1.0", content)
        text.tag_configure("link", foreground=self.theme.accent, underline=True)
        for link_start, link_end in link_url_spans(content):
            text.tag_add("link", f"1.0+{link_start}c", f"1.0+{link_end}c")
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
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        return text

    def _show_guide_window(self, path: Path) -> tk.Toplevel:
        existing = getattr(self, "_guide_dialog", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.deiconify()
                    existing.lift()
                    existing.focus_force()
                    return existing
            except tk.TclError:
                pass
            self._guide_dialog = None

        window = tk.Toplevel(self.root)
        self._guide_dialog = window
        window.title(APP_NAME + " — " + tr("win.guide"))
        window.configure(bg=self.theme.background)
        window.geometry("1020x700")
        window.grid_rowconfigure(0, weight=1)
        window.grid_columnconfigure(0, weight=1)

        body = tk.Frame(window, bg=self.theme.background)
        body.grid(row=0, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)

        nav = tk.Frame(body, bg=self.theme.panel, width=155)
        viewer = tk.Frame(body, bg=self.theme.background)
        content = path.read_text(encoding="utf-8", errors="replace")

        rich_frame = None
        rich_ready = False
        try:
            from .guide_html import GUIDE_SECTION_KEYS, guide_section_labels, render_guide_html
            from .i18n import get_language

            factory = self._guide_html_frame_factory
            if factory is None:
                from tkinterweb import HtmlFrame
                factory = HtmlFrame

            rich_frame = factory(
                viewer,
                messages_enabled=False,
                javascript_enabled=False,
                images_enabled=False,
                objects_enabled=False,
                forms_enabled=False,
                caches_enabled=False,
                dark_theme_enabled=True,
                on_link_click=self._open_guide_web_link,
            )
            rich_frame.grid(row=0, column=0, sticky="nsew")
            viewer.grid_rowconfigure(0, weight=1)
            viewer.grid_columnconfigure(0, weight=1)

            language = get_language()
            labels = guide_section_labels(language)

            def render_section(section_key: str) -> None:
                html_source = render_guide_html(
                    content,
                    section_key=section_key,
                    language=language,
                )
                rich_frame.load_html(html_source)
                self._guide_section_key = section_key

            render_section("start")
            nav.grid(row=0, column=0, sticky="nsw")
            viewer.grid(row=0, column=1, sticky="nsew")
            for row, section_key in enumerate(GUIDE_SECTION_KEYS):
                self._button(
                    nav,
                    labels[section_key],
                    lambda key=section_key: render_section(key),
                ).grid(row=row, column=0, sticky="ew", padx=8, pady=(8 if row == 0 else 3, 0))
            rich_ready = True
            self._guide_html_frame = rich_frame
        except Exception:
            if rich_frame is not None:
                try:
                    rich_frame.destroy()
                except Exception:
                    pass
            try:
                nav.destroy()
            except tk.TclError:
                pass
            body.grid_columnconfigure(0, weight=1)
            viewer.grid(row=0, column=0, sticky="nsew")
            self._show_guide_markdown_fallback(viewer, content)
            self._guide_html_frame = None

        bar = tk.Frame(window, bg=self.theme.panel)
        bar.grid(row=1, column=0, sticky="ew")
        self._button(bar, "Open File", lambda: _default_guide_opener(path)).grid(
            row=0, column=0, sticky="w", padx=10, pady=8
        )
        self._button(
            bar,
            "Close",
            lambda: window.destroy() if window.winfo_exists() else None,
        ).grid(row=0, column=1, sticky="w", pady=8)
        self._guide_rich_ready = rich_ready
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
        self._start_system_monitor()
        # First-run: open the setup wizard if no connectors exist
        try:
            instances = self.service.instances()
            if not instances:
                self._schedule_after(1500, self.open_setup_wizard)
        except Exception:
            pass
        self._monitor_tick()
        self._instance_refresh_tick()
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
            self._connector_counts = (0, 0)
            self._active_drift_count = 0
            self.overview_workers_value.configure(text="0 / 0")
            self.overview_connectors_value.configure(text="0", fg=self.theme.foreground)
            self._render_header_runtime_status()
            for button in (
                self.instance_start_button,
                self.instance_stop_button,
                self.instance_startall_button,
                self.instance_auto_button,
                self.instance_rescan_button,
            ):
                self._set_enabled(button, False)
            return
        # Single-flight: the 15s live tick must not stack state refreshes.
        if self._instance_states_active:
            return
        self._instance_states_active = True
        future = self._background_executor.submit(self._instance_states_with_activity)
        self._schedule_after(0, self._poll_instance_states, future)

    def _instance_states_with_cancel(self):
        states_fn = getattr(self.service, "instance_states_cancellable", None)
        if callable(states_fn):
            return states_fn(cancel_check=self._background_cancel_event.is_set)
        return getattr(self.service, "instance_states")()

    def _instance_states_with_activity(self):
        """Observe connector health + Serena active project off the Tk thread."""
        from .serena_activity import observe_serena_activity

        rows = []
        for instance, state in self._instance_states_with_cancel():
            if self._background_cancel_event.is_set():
                break
            try:
                activity = observe_serena_activity(instance.instance_root)
            except Exception:
                activity = None
            rows.append((instance, state, activity))
        return tuple(rows)

    def _instance_action_with_cancel(self, name: str, action: str):
        if action == "start":
            action_fn = getattr(self.service, "instance_action_cancellable", None)
            if callable(action_fn):
                return action_fn(
                    name,
                    action,
                    cancel_check=self._background_cancel_event.is_set,
                )
        return getattr(self.service, "instance_action")(name, action)

    def _log_connector_recovery_events(self) -> None:
        drain_fn = getattr(self.service, "drain_connector_recovery_events", None)
        if not callable(drain_fn):
            return
        try:
            events = drain_fn()
        except Exception:
            return
        for record in events:
            if not isinstance(record, ConnectorRecoveryRecord):
                continue
            self.log_activity(
                f"AUTO-RECOVER {record.instance_name} {record.state.value} "
                f"restart={record.restart_count}"
            )

    def _poll_instance_states(self, future: Future) -> None:
        if not future.done():
            self._schedule_after(25, self._poll_instance_states, future)
            return
        try:
            states = future.result()
        except Exception:
            self._instance_states_active = False
            self._rescan_summary_pending = False
            self._handle_error("INSTANCE_REFRESH_FAILED")
            return
        self._log_connector_recovery_events()
        self.instance_tree.delete(*self.instance_tree.get_children())
        self._instance_rows.clear()
        self._monitor_instances.clear()
        auto_fn = getattr(self.service, "instance_autostart", None)
        aliases_fn = getattr(self.service, "instance_aliases", None)
        aliases: dict[str, str] = {}
        if callable(aliases_fn):
            try:
                aliases = aliases_fn() or {}
            except Exception:
                aliases = {}
        drift_count = 0
        for instance, state, activity in states:
            auto = False
            if callable(auto_fn):
                try:
                    auto = bool(auto_fn(instance.name))
                except Exception:
                    auto = False

            active_project = "—"
            last_switch = "—"
            drift = False
            if state is InstanceHealthState.READY:
                active_name = getattr(activity, "active_project_name", None)
                active_path = getattr(activity, "active_project_path", None)
                switched_at = getattr(activity, "switched_at", None)
                if active_name:
                    if active_path:
                        bound_key = os.path.normcase(os.path.normpath(str(instance.project_path)))
                        active_key = os.path.normcase(os.path.normpath(str(active_path)))
                        drift = active_key != bound_key
                    active_project = f"{active_name} [DRIFT]" if drift else str(active_name)
                else:
                    active_project = "UNKNOWN"
                if switched_at is not None:
                    try:
                        last_switch = switched_at.strftime("%H:%M:%S")
                    except Exception:
                        last_switch = "—"

            tag = {
                InstanceHealthState.READY.value: "ready",
                InstanceHealthState.STOPPED.value: "idle",
            }.get(state.value, "warning")
            if drift:
                drift_count += 1
                tag = "warning"
            tunnel_cell = "-"
            if instance.tunnel_configured:
                tunnel_cell = (
                    f"...{instance.tunnel_suffix}"
                    if getattr(instance, "tunnel_suffix", "")
                    else "Y"
                )
            item = self.instance_tree.insert(
                "",
                "end",
                values=(
                    aliases.get(instance.name, instance.name),
                    instance.health_address.split(":")[-1],
                    state.value,
                    instance.project_path,
                    tunnel_cell,
                    "ON" if auto else "-",
                    active_project,
                    last_switch,
                    "Edit",
                ),
                tags=(tag,),
            )
            self._instance_rows[instance.name] = item
            self._monitor_instances[instance.name] = instance
        if not self.instance_tree.get_children():
            self.instance_tree.insert(
                "",
                "end",
                iid="__add_instance__",
                values=("+ Add Connector", "", "", "", "", "", "", "", ""),
                tags=("row-add",),
            )
        for button in (
            self.instance_start_button,
            self.instance_stop_button,
            self.instance_startall_button,
            self.instance_auto_button,
            self.instance_rescan_button,
        ):
            self._set_enabled(button, True)
        ready_connectors = sum(
            1
            for _instance, state, _activity in states
            if state.value == InstanceHealthState.READY.value
        )
        self._connector_counts = (ready_connectors, len(states))
        self._active_drift_count = drift_count
        self.overview_workers_value.configure(text=f"{ready_connectors} / {len(states)}")
        self.overview_connectors_value.configure(
            text=str(drift_count),
            fg=self.theme.warning if drift_count else self.theme.foreground,
        )
        self._render_header_runtime_status()
        self._set_enabled(self.brain_button, self._has_settings_service())
        self._instance_states_active = False
        if self._rescan_summary_pending:
            self._rescan_summary_pending = False
            stopped = len(states) - ready_connectors
            self.log_activity(
                f"RESCAN       พบ {len(states)} ตัวเชื่อม: "
                f"{ready_connectors} READY, {stopped} STOPPED"
            )

    def _selected_instance_name(self) -> str | None:
        selection = self.instance_tree.selection()
        if not selection:
            return None
        for name, item in self._instance_rows.items():
            if item == selection[0]:
                return name
        return None

    def _handle_inline_click(self, tree, row, column, edit_column, on_edit, on_add):
        """Route a row click to inline actions.

        ``+ Add ...`` synthetic rows open the matching add dialog from any
        column; data rows open the row editor only from the trailing EDIT
        column. Returns "break" when the default selection handling should
        be suppressed, otherwise None so Tk behavior continues untouched.
        """
        if not row:
            return None
        tags = tree.item(row, "tags") or ()
        if row.startswith("__add_") or "row-add" in tags:
            on_add()
            return "break"
        if column == edit_column:
            tree.selection_set(row)
            tree.focus(row)
            on_edit()
            return "break"
        return None

    def _on_worker_tree_click(self, event):
        tree = self.worker_tree
        if tree.identify_region(event.x, event.y) not in ("cell", "tree"):
            return None
        return self._handle_inline_click(
            tree,
            tree.identify_row(event.y),
            tree.identify_column(event.x),
            self._worker_edit_column,
            self.open_rename_worker_dialog,
            self.open_add_worker_dialog,
        )

    def _on_instance_tree_click(self, event):
        tree = self.instance_tree
        if tree.identify_region(event.x, event.y) not in ("cell", "tree"):
            return None
        return self._handle_inline_click(
            tree,
            tree.identify_row(event.y),
            tree.identify_column(event.x),
            self._instance_edit_column,
            self.open_edit_instance_dialog,
            self.open_add_instance_dialog,
        )

    def _on_project_tree_click(self, event):
        tree = self.project_list
        if tree.identify_region(event.x, event.y) not in ("cell", "tree"):
            return None
        return self._handle_inline_click(
            tree,
            tree.identify_row(event.y),
            tree.identify_column(event.x),
            self._project_edit_column,
            self.assign_selected,
            self.add_project,
        )

    def open_edit_instance_dialog(self) -> tk.Toplevel | None:
        """Unified connector editor: alias, Tunnel ID, and project path."""
        existing = getattr(self, "_edit_dialog", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return existing
        name = self._selected_instance_name()
        if name is None:
            self._handle_error("SELECT_INSTANCE")
            return None
        aliases = {}
        loader = getattr(self.service, "instance_aliases", None)
        if callable(loader):
            try:
                aliases = loader() or {}
            except Exception:
                aliases = {}
        current_alias = aliases.get(name, name)
        instance = self._monitor_instances.get(name)
        current_project = getattr(instance, "project_path", "") or ""

        dialog = tk.Toplevel(self.root)
        self._edit_dialog = dialog
        dialog.title(f'{APP_NAME} — {tr("dlg.edit.connector.title")} — {name}')
        dialog.configure(bg=self.theme.panel)
        dialog.transient(self.root)
        dialog.resizable(True, False)
        frame = tk.Frame(dialog, bg=self.theme.panel, padx=14, pady=14)
        frame.pack(fill="both", expand=True)
        frame.grid_columnconfigure(1, weight=1)
        tk.Label(
            frame,
            text=f'> {tr("dlg.edit.connector.header")}  {name}',
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
        self._edit_name_entry = ttk.Entry(frame, font=(self.theme.monospace_font, 10))
        self._edit_name_entry.insert(0, current_alias)
        self._edit_name_entry.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 8))

        tk.Label(
            frame,
            text=tr("dlg.edit.connector.tunnel"),
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
            justify="left",
        ).grid(row=3, column=0, columnspan=2, sticky="w")
        self._tunnel_entry = ttk.Entry(frame, width=52)
        self._tunnel_entry.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4, 2))
        tunnel_now = getattr(instance, "tunnel_suffix", "")
        tunnel_hint = (
            f"ปัจจุบัน: ...{tunnel_now}" if tunnel_now else "ปัจจุบัน: ยังไม่ตั้ง Tunnel ID"
        )
        self._tunnel_status = tk.Label(
            frame,
            text=tunnel_hint,
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
        )
        # Masked-current alias: tests (and future callers) read the hint here.
        self._edit_tunnel_current = self._tunnel_status
        self._tunnel_status.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self._tunnel_entry.bind("<KeyRelease>", lambda _e: self._validate_tunnel_entry())

        tk.Label(
            frame,
            text=tr("dlg.edit.connector.project"),
            bg=self.theme.panel,
            fg=self.theme.muted,
            font=(self.theme.monospace_font, 9),
            justify="left",
        ).grid(row=6, column=0, columnspan=2, sticky="w")
        self._edit_project_entry = ttk.Entry(frame, width=64)
        self._edit_project_entry.insert(0, current_project)
        self._edit_project_entry.grid(row=7, column=0, sticky="ew", pady=(4, 2))
        self._button(
            frame,
            "เลือกโฟลเดอร์...",
            lambda: self._edit_project_entry.insert(0, self._directory_picker()),
        ).grid(row=7, column=1, sticky="w", padx=(6, 0))

        def save() -> None:
            # DEFECT_LESSONS #2: read every widget value before destroy().
            new_alias = self._edit_name_entry.get().strip()
            tunnel = self._tunnel_entry.get().strip()
            new_project = self._edit_project_entry.get().strip()
            if not new_alias:
                self._handle_error("INSTANCE_FIELDS_REQUIRED")
                return
            if dialog.winfo_exists():
                dialog.destroy()
            self._save_edit_instance_dialog_values(
                name, current_alias, current_project, new_alias, tunnel, new_project
            )

        self._button(frame, "บันทึก", save).grid(row=8, column=0, sticky="w", pady=(12, 0))
        self._button(
            frame, "ยกเลิก", lambda: dialog.destroy() if dialog.winfo_exists() else None
        ).grid(row=8, column=1, sticky="w", pady=(12, 0))
        self._edit_name_entry.focus_set()
        return dialog

    def _save_edit_instance_dialog_values(
        self,
        name: str,
        current_alias: str,
        current_project: str,
        new_alias: str,
        tunnel: str,
        new_project: str,
    ) -> None:
        """Apply only the changed fields, in a safe order, then refresh."""
        changed = False
        if tunnel:
            writer = getattr(self.service, "set_instance_tunnel_id", None)
            if not callable(writer):
                self._handle_error("TUNNEL_SETUP_NOT_AVAILABLE")
                return
            try:
                writer(name, tunnel)
            except Exception:
                self._handle_error("TUNNEL_ID_INVALID")
                return
            self.log_activity(f"Tunnel       {name} ID SAVED")
            changed = True
        if new_project and new_project != current_project:
            rebind_fn = getattr(self.service, "rebind_instance", None)
            if callable(rebind_fn):
                try:
                    result = rebind_fn(name, new_project)
                except Exception:
                    self._handle_error("REBIND_FAILED")
                    return
                if result == "REBOUND":
                    self.log_activity(
                        f"Rebind       {name} -> {new_project} (restart ตัวเชื่อมเพื่อให้มีผล)"
                    )
                    changed = True
        if new_alias != current_alias:
            rename_fn = getattr(self.service, "rename_instance", None)
            if not callable(rename_fn):
                self._handle_error("INSTANCE_RENAME_NOT_AVAILABLE")
                return
            try:
                display = rename_fn(name, new_alias)
            except Exception as exc:
                self._handle_error(getattr(exc, "code", "INSTANCE_RENAME_FAILED"))
                return
            self.log_activity(f"Rename       {name} -> {display}")
            changed = True
        if changed:
            self.refresh_instances()

    def _submit_instance_action(self, action: str, name: str) -> None:
        self.log_activity(f"{action:<12} {name} QUEUED")
        command = action.split("-", 1)[0].lower()
        future = self._background_executor.submit(
            self._instance_action_with_cancel, name, command
        )
        if command == "start":
            self._instance_start_futures.add(future)
        self._schedule_after(0, self._poll_instance_action, action, name, future)

    def _poll_instance_action(self, action: str, name: str, future: Future) -> None:
        if not future.done():
            self._schedule_after(25, self._poll_instance_action, action, name, future)
            return
        self._instance_start_futures.discard(future)
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
        self._instance_start_futures.add(future)
        self._schedule_after(0, self._poll_start_all, future)

    def _wait_for_instance_starts(self) -> None:
        """Give cooperative start cancellation a bounded handoff before stop-all."""
        pending = tuple(self._instance_start_futures)
        if pending:
            completed, _unfinished = wait(pending, timeout=4.0)
            self._instance_start_futures.difference_update(completed)

    def _start_all_worker(self):
        results: list[tuple[str, str]] = []
        for instance, state in self._instance_states_with_cancel():
            if self._background_cancel_event.is_set():
                break
            if state is InstanceHealthState.READY:
                continue
            try:
                outcome = self._instance_action_with_cancel(instance.name, "start")
                results.append((instance.name, outcome.result_code.value))
            except Exception:
                results.append((instance.name, "ERROR"))
        return results

    def _poll_start_all(self, future: Future) -> None:
        if not future.done():
            self._schedule_after(25, self._poll_start_all, future)
            return
        self._instance_start_futures.discard(future)
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
        # WO-P1-068: the poll logs a found/READY/STOPPED summary when it
        # lands, so the button never looks like it silently did something.
        self._rescan_summary_pending = True
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
        existing = getattr(self, "_brain_dialog", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return existing
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
        self._brain_dialog = dialog
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
        saved_summary = " · ".join(
            tuple(saved.brain_folders) + tuple(saved.brain_entry_files)
        ) or "cleared"
        self.log_activity(f"Brain        {saved_summary} SAVED")
        self.log_activity("Brain        NOTE: restart running connectors to activate")
        # Keep the dialog open with a green confirmation so the operator
        # sees exactly which paths were saved (trial feedback), plus the
        # activation rule — the brain materializes only at connector Start,
        # so already-running chats stay brainless until a restart.
        status = getattr(self, "_brain_status", None)
        if status is not None and status.winfo_exists():
            status.configure(
                text=(
                    f"บันทึกแล้ว ✓  {saved_summary}\n"
                    "⚠ สมองมีผลเมื่อตัวเชื่อม Start — รีสตาร์ทตัวเชื่อมที่กำลังรัน"
                    "เพื่อให้แชทปัจจุบันใช้สมองใหม่"
                ),
                fg=self.theme.ready,
            )

    def _autostart_flagged_instances(self) -> None:
        if not self._has_instance_service():
            return
        if not callable(getattr(self.service, "autostart_instance_names", None)):
            return
        future = self._background_executor.submit(self._autostart_worker)
        self._instance_start_futures.add(future)
        self._schedule_after(0, self._poll_autostart, future)

    def _autostart_worker(self):
        results: list[tuple[str, str]] = []
        for name in getattr(self.service, "autostart_instance_names")():
            if self._background_cancel_event.is_set():
                break
            try:
                outcome = self._instance_action_with_cancel(name, "start")
                results.append((name, outcome.result_code.value))
            except Exception:
                results.append((name, "ERROR"))
        return results

    def _poll_autostart(self, future: Future) -> None:
        if not future.done():
            self._schedule_after(25, self._poll_autostart, future)
            return
        self._instance_start_futures.discard(future)
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
        self._schedule_after(
            0,
            self._poll_upstream,
            future,
            present,
        )
    def _poll_upstream(self, future: Future, present) -> None:
        if not future.done():
            self._schedule_after(25, self._poll_upstream, future, present)
            return
        try:
            status = future.result()
        except Exception:
            self._set_enabled(self.upstream_button, True)
            self._handle_error("UPSTREAM_CHECK_FAILED")
            return
        present(status)
