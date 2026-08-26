import json
from pathlib import Path

import click
from flask import Flask
from sqlalchemy import select
from sqlalchemy.exc import DataError, IntegrityError

from .extensions import db
from .models import Admin, EditionStatus, Olympiad, OlympiadEdition
from .services.catalog import ValidationError, upsert_catalog_record


def register_commands(app: Flask) -> None:
    @app.cli.command("create-admin")
    @click.option("--username", prompt=True, help="Логин администратора")
    @click.password_option(confirmation_prompt=True)
    def create_admin(username: str, password: str) -> None:
        """Create an administrator or replace the password of an existing one."""
        username = username.strip()
        if not username:
            raise click.ClickException("Логин не может быть пустым")
        if len(username) > 80:
            raise click.ClickException("Логин не может быть длиннее 80 символов")
        if not password.strip() or len(password) < 12:
            raise click.ClickException(
                "Пароль должен содержать не менее 12 символов и не может "
                "состоять только из пробелов"
            )
        admin = db.session.scalar(select(Admin).where(Admin.username == username))
        if admin is None:
            admin = Admin(username=username, password_hash="")
            db.session.add(admin)
        admin.set_password(password)
        admin.is_active = True
        db.session.commit()
        click.echo(f"Администратор {username} готов.")

    @app.cli.command("import-catalog")
    @click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
    @click.option(
        "--sync",
        is_flag=True,
        help=(
            "Считать файл полным снимком затронутых учебных годов и архивировать "
            "отсутствующие в нём сезоны."
        ),
    )
    def import_catalog(source: Path, sync: bool) -> None:
        """Idempotently import catalog records from a JSON file."""
        try:
            document = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise click.ClickException(f"Не удалось прочитать JSON: {exc}") from exc

        records = document.get("records") if isinstance(document, dict) else document
        if not isinstance(records, list):
            raise click.ClickException("Ожидался массив records")

        imported_keys: set[tuple[str, str]] = set()
        for index, record in enumerate(records, start=1):
            if not isinstance(record, dict):
                raise click.ClickException(f"Запись {index} должна быть объектом")
            slug = str(record.get("slug") or "").strip()
            academic_year = str(record.get("academic_year") or "").strip()
            key = (slug, academic_year)
            if key in imported_keys:
                raise click.ClickException(
                    f"Повторная запись для {slug or '<без slug>'}, {academic_year or '<без года>'}"
                )
            imported_keys.add(key)

        archived_count = 0
        try:
            for record in records:
                upsert_catalog_record(record)
            if sync and imported_keys:
                academic_years = {academic_year for _, academic_year in imported_keys}
                editions = db.session.scalars(
                    select(OlympiadEdition)
                    .join(Olympiad, OlympiadEdition.olympiad_id == Olympiad.id)
                    .where(OlympiadEdition.academic_year.in_(academic_years))
                ).all()
                for edition in editions:
                    if (edition.olympiad.slug, edition.academic_year) in imported_keys:
                        continue
                    if edition.status != EditionStatus.ARCHIVED:
                        edition.status = EditionStatus.ARCHIVED
                        archived_count += 1
            db.session.commit()
        except (ValidationError, DataError, IntegrityError, TypeError, KeyError) as exc:
            db.session.rollback()
            raise click.ClickException(f"Импорт отменён: {exc}") from exc
        message = f"Импортировано записей: {len(records)}"
        if sync:
            message += f"; архивировано отсутствующих сезонов: {archived_count}"
        click.echo(message)
