from django.urls import path
from .api import *

urlpatterns = [
    path('expired/', CheckSessionExpiredView.as_view(), name='check-session-expired'),
    path('run/', RunCodeView.as_view(), name='run_code'),
    path('code/', GetCodeView.as_view(), name='get_code'),
    path('agent/', GetAgentView.as_view(), name='get_agent'),


    path('jobs/', JobListView.as_view(), name='job-list'),
    path('jobs/create/', JobCreateView.as_view(), name='job-create'),
    path('interviews/create/', InterviewCreateView.as_view(), name='interview-create'),
    path('interviews/', UserInterviewListView.as_view(), name='user-interviews'),
    path('room/create/', InterviewRoomCreateView.as_view(), name='room-create'),
    path('material/create/', PreparationMaterialCreateView.as_view(), name='preparation-material-create'),
    path('material/delete/', PreparationMaterialDeleteView.as_view(), name='preparation-material-delete'),
 

    path('interviews/<int:pk>/', InterviewDetailView.as_view(), name='interview-detail'),
    path('interviews/<int:pk>/update/', InterviewUpdateView.as_view(), name='interview-update'),
    path('interviews/<int:pk>/delete/', InterviewDeleteView.as_view(), name='interview-delete'),

    path('jobs/<int:pk>/', JobDetailView.as_view(), name='job-detail'),
    path('jobs/<int:pk>/update/', JobUpdateView.as_view(), name='job-update'),
    path('jobs/<int:pk>/delete/', JobDeleteView.as_view(), name='job-delete'),


    path('material/<int:id>/', PreparationMaterialDetailView.as_view(), name='preparation-material-detail'),
    path('material/<int:material_id>/mark/', PreparationMaterialMarkingView.as_view(), name='preparation-material-mark'),



    path('room/<int:id>/', InterviewRoomDetailView.as_view(), name='room-detail'),
    path('room/<int:material_id>/mark/', InterviewRoomMarkingView.as_view(), name='room-mark'),




    path('p-blocks/<int:block_id>/update/', PreparationBlockUpdateView.as_view(), name='preparation-block-update'),
    # path('preparation-blocks/<int:block_id>/', PreparationBlockDetailView.as_view(), name='preparation-block-detail'),


    path('code/<int:id>/update/', CodingQuestionUpdateView.as_view(), name='preparation-code-update'),


    path('i-blocks/<int:block_id>/update/', InterviewBlockUpdateView.as_view(), name='interview-block-update'),
    # path('preparation-blocks/<int:block_id>/', PreparationBlockDetailView.as_view(), name='preparation-block-detail'),


    path('icode/<int:id>/update/', InterviewCodingQuestionUpdateView.as_view(), name='interview-code-update'),


    path('ask-agent/<int:session_id>/', AskAgentView.as_view(), name='ask-agent'),





]
