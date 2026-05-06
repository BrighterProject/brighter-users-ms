from tortoise import migrations
from tortoise.migrations import operations as ops
from tortoise import fields

class Migration(migrations.Migration):
    dependencies = [('models', '0002_auto_20260504_0137')]

    initial = False

    operations = [
        ops.AddField(
            model_name='User',
            name='locale',
            field=fields.CharField(default='en', max_length=10),
        ),
    ]
