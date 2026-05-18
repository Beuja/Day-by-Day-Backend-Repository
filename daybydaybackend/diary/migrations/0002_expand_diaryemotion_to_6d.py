from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("diary", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="diaryemotion",
            name="anger",
            field=models.FloatField(default=0.0, help_text="분노 감정 점수 (0.0에서 1.0 사이)"),
        ),
        migrations.AddField(
            model_name="diaryemotion",
            name="fear",
            field=models.FloatField(default=0.0, help_text="두려움 감정 점수 (0.0에서 1.0 사이)"),
        ),
        migrations.AddField(
            model_name="diaryemotion",
            name="joy",
            field=models.FloatField(default=0.0, help_text="기쁨 감정 점수 (0.0에서 1.0 사이)"),
        ),
        migrations.AddField(
            model_name="diaryemotion",
            name="sadness",
            field=models.FloatField(default=0.0, help_text="슬픔 감정 점수 (0.0에서 1.0 사이)"),
        ),
        migrations.AddField(
            model_name="diaryemotion",
            name="surprise",
            field=models.FloatField(default=0.0, help_text="놀람 감정 점수 (0.0에서 1.0 사이)"),
        ),
        migrations.AddField(
            model_name="diaryemotion",
            name="trust",
            field=models.FloatField(default=0.0, help_text="신뢰 감정 점수 (0.0에서 1.0 사이)"),
        ),
    ]
