from django.db import migrations, models



def populate_tipos(apps, schema_editor):
    TipoTransacao = apps.get_model('curriculum', 'TipoTransacao')
    tipos = ['Uso de crédito', 'Compra de crédito', 'Reversão']
    for nome in tipos:
        TipoTransacao.objects.get_or_create(nome=nome)

class Migration(migrations.Migration):
    dependencies = [
        ('curriculum', '0027_education_is_current_executableproject_is_current_and_more'),
    ]
    operations = [
        migrations.RunPython(populate_tipos),
    ]