from django.contrib import admin
from . import models

# Register your models here.
admin.site.register([models.Repository, models.Branch, models.Change,
    models.Issue,
    models.IntegrationType, models.BuildProject, models.Build, models.PlatformBuild, models.Platform,
    models.ElectricCommanderBuild, models.ElectricCommanderPlatformBuild, 
    models.JenkinsPlatformBuild, models.JenkinsBuild])