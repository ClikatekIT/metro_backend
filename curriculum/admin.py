from django.contrib import admin
from .models import (
    User,
    Education,
    ShortEducation,
    Experience,
    ExecutableProject,
    Internship,
    Volunteer,
    Award,
    PersonalInfo,
    Skill,
    Language,
    Software,
    Referenc,
    CV,
    TipoTransacao,
    Transacao,
    Credit,
    ExperienceJD,
    EducationJD,
    JobDescription,
    LanguageJD,
    SoftwareJD,
)

admin.site.register(ExperienceJD)
admin.site.register(EducationJD)
admin.site.register(LanguageJD)
admin.site.register(SoftwareJD)
admin.site.register(JobDescription)
admin.site.register(User)
admin.site.register(Education)
admin.site.register(ShortEducation)
admin.site.register(Experience)
admin.site.register(ExecutableProject)
admin.site.register(Internship)
admin.site.register(Volunteer)
admin.site.register(Award)
admin.site.register(PersonalInfo)
admin.site.register(Skill)
admin.site.register(Language)
admin.site.register(Software)
admin.site.register(Referenc)
admin.site.register(CV)
admin.site.register(TipoTransacao)
admin.site.register(Transacao)
admin.site.register(Credit)

# Register your models here.
