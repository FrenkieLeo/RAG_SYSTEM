from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions


DEFAULT_ALLOWED_PERMISSIONS = UserAccessPermissions(0xFFFFFFFC)


class PdfBatchLockerError(Exception):
    """Base exception for user-facing batch encryption failures."""


class PasswordValidationError(PdfBatchLockerError):
    """Raised when the supplied passwords cannot be used safely."""


@dataclass(frozen=True)
class EncryptionOptions:
    source_password: str = ""
    open_password: str = ""
    owner_password: str = ""
    restrict_print: bool = True
    restrict_copy: bool = True
    restrict_modify: bool = True
    restrict_comment: bool = True
    restrict_fill_forms: bool = True
    restrict_assemble: bool = True
    overwrite: bool = False
    recursive: bool = False


@dataclass(frozen=True)
class BatchItemResult:
    source: Path
    output: Path
    ok: bool
    message: str


ProgressCallback = Callable[[int, int, BatchItemResult], None]


def validate_passwords(
    *,
    open_password_enabled: bool,
    open_password: str,
    open_password_confirm: str,
    owner_password: str,
    owner_password_confirm: str,
    restrictions_enabled: bool,
) -> None:
    if open_password_enabled:
        _validate_password_pair("打开密码", open_password, open_password_confirm)
    elif open_password:
        raise PasswordValidationError("未勾选设置打开密码时，请清空打开密码。")

    if restrictions_enabled:
        _validate_password_pair("权限密码", owner_password, owner_password_confirm)
    elif owner_password or owner_password_confirm:
        _validate_password_pair("权限密码", owner_password, owner_password_confirm)


def build_permissions(options: EncryptionOptions) -> UserAccessPermissions:
    permissions = DEFAULT_ALLOWED_PERMISSIONS

    if options.restrict_print:
        permissions &= ~UserAccessPermissions.PRINT
        permissions &= ~UserAccessPermissions.PRINT_TO_REPRESENTATION
    if options.restrict_copy:
        permissions &= ~UserAccessPermissions.EXTRACT
        permissions &= ~UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS
    if options.restrict_modify:
        permissions &= ~UserAccessPermissions.MODIFY
    if options.restrict_comment:
        permissions &= ~UserAccessPermissions.ADD_OR_MODIFY
    if options.restrict_fill_forms:
        permissions &= ~UserAccessPermissions.FILL_FORM_FIELDS
    if options.restrict_assemble:
        permissions &= ~UserAccessPermissions.ASSEMBLE_DOC

    return permissions


def collect_pdf_files(input_dir: Path, *, recursive: bool, exclude_dir: Path | None = None) -> list[Path]:
    input_dir = input_dir.resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise PdfBatchLockerError(f"输入文件夹不存在：{input_dir}")

    exclude_resolved = exclude_dir.resolve() if exclude_dir else None
    pattern = "**/*.pdf" if recursive else "*.pdf"
    pdf_files: list[Path] = []

    for path in sorted(input_dir.glob(pattern), key=lambda item: str(item).lower()):
        if not path.is_file():
            continue
        if exclude_resolved and _is_relative_to(path.resolve(), exclude_resolved):
            continue
        pdf_files.append(path)

    return pdf_files


def encrypt_pdf(source: Path, output: Path, options: EncryptionOptions) -> None:
    source = source.resolve()
    output = output.resolve()

    if source == output:
        raise PdfBatchLockerError("输出文件不能覆盖原文件，请选择不同的输出文件夹。")
    if output.exists() and not options.overwrite:
        raise PdfBatchLockerError("输出文件已存在，未勾选覆盖。")

    output.parent.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(str(source))
    if reader.is_encrypted:
        if not options.source_password:
            raise PdfBatchLockerError("源 PDF 已加密，请填写源 PDF 密码。")
        if not reader.decrypt(options.source_password):
            raise PdfBatchLockerError("源 PDF 密码不正确。")

    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    writer.encrypt(
        user_password=options.open_password,
        owner_password=options.owner_password or None,
        permissions_flag=build_permissions(options),
        algorithm="AES-256",
    )

    with output.open("wb") as stream:
        writer.write(stream)


def batch_encrypt_folder(
    input_dir: Path,
    output_dir: Path,
    options: EncryptionOptions,
    progress: ProgressCallback | None = None,
) -> list[BatchItemResult]:
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    files = collect_pdf_files(input_dir, recursive=options.recursive, exclude_dir=output_dir)
    if not files:
        raise PdfBatchLockerError("输入文件夹中没有找到 PDF 文件。")

    results: list[BatchItemResult] = []
    total = len(files)
    for index, source in enumerate(files, start=1):
        relative = source.relative_to(input_dir)
        output = output_dir / relative
        try:
            encrypt_pdf(source, output, options)
        except Exception as exc:  # noqa: BLE001 - report per-file failures to the GUI.
            result = BatchItemResult(source=source, output=output, ok=False, message=str(exc))
        else:
            result = BatchItemResult(source=source, output=output, ok=True, message="完成")
        results.append(result)
        if progress:
            progress(index, total, result)

    return results


def summarize_results(results: Iterable[BatchItemResult]) -> tuple[int, int]:
    succeeded = 0
    failed = 0
    for result in results:
        if result.ok:
            succeeded += 1
        else:
            failed += 1
    return succeeded, failed


def _validate_password_pair(label: str, password: str, confirm: str) -> None:
    if password != confirm:
        raise PasswordValidationError(f"{label}两次输入不一致。")
    if not 6 <= len(password) <= 128:
        raise PasswordValidationError(f"{label}长度必须为 6-128 位。")


def _is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
    except ValueError:
        return False
    return True
