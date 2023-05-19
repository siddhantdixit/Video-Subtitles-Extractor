from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="hello"),
    path("upload",views.upload_file,name="fileupload"),
    path("subtitle/<str:fileid>",views.request_subtitle)
]