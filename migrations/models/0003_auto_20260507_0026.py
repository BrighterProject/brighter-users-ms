from tortoise.migrations import Migration, RunPython


async def add_locale(apps, schema_editor) -> None:
    await schema_editor._run_sql(
        'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "locale" VARCHAR(10) NOT NULL DEFAULT \'en\';'
    )


async def drop_locale(apps, schema_editor) -> None:
    await schema_editor._run_sql('ALTER TABLE "user" DROP COLUMN IF EXISTS "locale";')


class Migration(Migration):
    dependencies = [('models', '0002_auto_20260504_0137')]

    initial = False

    operations = [
        RunPython(add_locale, drop_locale),
    ]
