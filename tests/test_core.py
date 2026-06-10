from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions

from pdf_batch_locker.core import (
    EncryptionOptions,
    PasswordValidationError,
    batch_encrypt_folder,
    build_permissions,
    collect_pdf_files,
    encrypt_pdf,
    validate_passwords,
)


def test_build_permissions_removes_selected_restrictions() -> None:
    permissions = build_permissions(EncryptionOptions())

    assert not permissions & UserAccessPermissions.PRINT
    assert not permissions & UserAccessPermissions.PRINT_TO_REPRESENTATION
    assert not permissions & UserAccessPermissions.EXTRACT
    assert not permissions & UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS
    assert not permissions & UserAccessPermissions.MODIFY
    assert not permissions & UserAccessPermissions.ADD_OR_MODIFY
    assert not permissions & UserAccessPermissions.FILL_FORM_FIELDS
    assert not permissions & UserAccessPermissions.ASSEMBLE_DOC


def test_validate_passwords_requires_owner_password_for_restrictions() -> None:
    with pytest.raises(PasswordValidationError, match="权限密码长度"):
        validate_passwords(
            open_password_enabled=False,
            open_password="",
            open_password_confirm="",
            owner_password="",
            owner_password_confirm="",
            restrictions_enabled=True,
        )


def test_encrypt_pdf_restricts_permissions(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _create_pdf(source)

    encrypt_pdf(
        source,
        output,
        EncryptionOptions(open_password="reader123", owner_password="owner123"),
    )

    reader = PdfReader(str(output))
    assert reader.is_encrypted
    assert reader.decrypt("reader123")

    permissions = reader.user_access_permissions
    assert not permissions & UserAccessPermissions.PRINT
    assert not permissions & UserAccessPermissions.EXTRACT
    assert not permissions & UserAccessPermissions.ADD_OR_MODIFY
    assert not permissions & UserAccessPermissions.ASSEMBLE_DOC


def test_batch_encrypt_folder_preserves_relative_paths(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    nested_dir = input_dir / "nested"
    output_dir = tmp_path / "output"
    nested_dir.mkdir(parents=True)
    _create_pdf(input_dir / "a.pdf")
    _create_pdf(nested_dir / "b.pdf")

    results = batch_encrypt_folder(
        input_dir,
        output_dir,
        EncryptionOptions(owner_password="owner123", recursive=True),
    )

    assert all(result.ok for result in results)
    assert (output_dir / "a.pdf").exists()
    assert (output_dir / "nested" / "b.pdf").exists()


def test_collect_pdf_files_skips_output_folder_when_recursive(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    output_dir = input_dir / "encrypted"
    output_dir.mkdir(parents=True)
    _create_pdf(input_dir / "a.pdf")
    _create_pdf(output_dir / "already.pdf")

    files = collect_pdf_files(input_dir, recursive=True, exclude_dir=output_dir)

    assert files == [input_dir.resolve() / "a.pdf"]


def _create_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with path.open("wb") as stream:
        writer.write(stream)
