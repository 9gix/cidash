from django.db import models
from django.db.models import Q

class BuildStatus:
    PASSED = 0
    FAILED = 1
    SKIPPED = 2
    ABORTED = 3

BUILD_STATUS_CHOICES = (
    (BuildStatus.PASSED, 'PASSED'),
    (BuildStatus.FAILED, 'FAILED'),
    (BuildStatus.SKIPPED, 'SKIPPED'),
    (BuildStatus.ABORTED, 'ABORTED'),
)

class SCM:
    GIT = 0
    P4 = 1
    TFS = 2
    
SCM_CHOICES = (
    (SCM.GIT, 'Git'),
    (SCM.P4, 'Perforce'),
    (SCM.TFS, 'TFS'),
)


class BuildProject(models.Model):
    name = models.CharField(max_length=100)


class Platform(models.Model):
    name = models.CharField(max_length=40)

class BuildQuerySet(models.QuerySet):
    def good_builds(self, project):
        q = Q(status=BuildStatus.PASSED)
        if project:
            Q(project=project)
        return self.filter(q)
        
class BuildManager(models.Manager):
    def get_queryset(self):
        return BuildQuerySet(self.model, using=self._db)

    def last_good_build(self, project):
        return self.good_builds(project).order_by('started').last()
    
    def prev_good_build(self, build):
        build = self.good_builds(project=build.project).filter(started__date__lt=build.started).order_by('started').last()


class Build(models.Model):
    """Abstract Model for Build.
    This model has to be implemented according to their specific orchestration tools.
    See JenkinsBuild as an example implementation.
    """

    project = models.ForeignKey('BuildProject', on_delete=models.PROTECT)
    ci_build_id = models.CharField(max_length=64)

    status = models.SmallIntegerField(blank=True, null=True, choices=BUILD_STATUS_CHOICES)

    started = models.DateTimeField(help_text="Build Started Timestamp", blank=True, null=True)
    finished = models.DateTimeField(help_text="Build Finished Timestamp", blank=True, null=True)

    # The first harvest timestamp
    created = models.DateTimeField(auto_now_add=True, help_text="First Harvest Timestamp")
    # The last harvest timestamp
    modified = models.DateTimeField(auto_now=True, help_text="Last Harvest Timestamp")

    integration_type = models.ForeignKey('IntegrationType', on_delete=models.PROTECT)

    last_change = models.ForeignKey('Change', on_delete=models.PROTECT)

    def changes_included(self):
        prev_good_build = self.project.builds.prev_good_build(self)
        if prev_good_build:
            prev_good_change = prev_good_build.last_change
            Change.changes.since(last_good_change)

    objects = BuildManager()


class PlatformBuild(Build):
    """Abstract Model for Platform specific Build.
    This model has to be implemented according to their specific orchestration tools.
    See JenkinsPlatformBuild for example
    """
    platform = models.ForeignKey('Platform', on_delete=models.PROTECT)


class IntegrationType(models.Model):
    name = models.CharField(max_length=30)
    abbrev = models.CharField(max_length=5)
    description = models.TextField(blank=True)



class ChangeQuerySet(models.QuerySet):

    def since(self, change):
        q = Q(pk=change.pk)
        for child in change.children.all():
            q |= Q(pk__in=self.since(child))
        return self.filter(q)

    def until(self, change):
        q = Q(pk=change.pk)
        if change.parent:
            q |= Q(pk__in=self.until(change.parent))
        return self.filter(q)

class Change(models.Model):
    revision = models.CharField(max_length=40, help_text="Tracking Revision or Commit Hash")
    summary = models.CharField(max_length=250)
    description = models.TextField(blank=True)
    author = models.CharField(max_length=100)
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name='children')
    merges_to = models.ManyToManyField('self', related_name='merges_from', blank=True)
    
    timestamp = models.DateTimeField()
    branch = models.ForeignKey('Branch', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('revision', 'branch')

    changeset = ChangeQuerySet.as_manager()


class Branch(models.Model):
    name = models.CharField(max_length=150)
    repository = models.ForeignKey('Repository', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('name', 'repository')


class Repository(models.Model):
    name = models.CharField(max_length=100)
    url = models.URLField()
    scm = models.SmallIntegerField(choices=SCM_CHOICES)

    class Meta:
        unique_together = ('name', 'url', 'scm')


class IssueTrackingSystem:
    """Issue Tracking System"""
    JIRA = 0
    TFS = 1

TRACKING_SYSTEM_CHOICES = (
    (IssueTrackingSystem.JIRA, 'JIRA'),
    (IssueTrackingSystem.TFS, 'TFS'),
)

class Issue(models.Model):
    tracking_code = models.CharField(max_length=32)
    tracking_system = models.SmallIntegerField(choices=TRACKING_SYSTEM_CHOICES)
    change = models.ForeignKey('Change', on_delete=models.CASCADE, null=True, blank=True, related_name='resolved_issues')

    class Meta:
        unique_together = ('tracking_code', 'tracking_system')


# HARVESTER SPECIFIC Build Implementation

# Electric Commander
class ElectricCommanderBuild(Build):
    procedure_name = models.CharField(max_length=100)
    procedure_step = models.CharField(max_length=100)

class ElectricCommanderPlatformBuild(PlatformBuild):
    procedure_name = models.CharField(max_length=100)
    procedure_step = models.CharField(max_length=100)

# Jenkins
class JenkinsBuild(Build):
    jenkins_project_name = models.CharField(max_length=100)

class JenkinsPlatformBuild(PlatformBuild):
    jenkins_project_name = models.CharField(max_length=100)

