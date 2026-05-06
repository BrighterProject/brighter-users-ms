from tortoise.migrations import Migration, SQLOperation


class Migration(Migration):
    dependencies = [('models', '0002_auto_20260504_0137')]

    initial = False

    operations = [
        SQLOperation('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS "locale" VARCHAR(10) NOT NULL DEFAULT \'en\';', []),
    ]
