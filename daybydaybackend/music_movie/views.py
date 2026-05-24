from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from daybydaybackend.diary.models import Diary
from . import serializers
from . import services

@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_music_view(request, diary_id):
    diary_obj = get_object_or_404(Diary, id=diary_id, user=request.user)
    
    # 1. 달력 클릭 시 과거 저장 데이터 복원 조회 (GET)
    if request.method == 'GET':
        data = services.get_saved_music_metadata(diary_obj)
        serializer = serializers.MusicResponseSerializer(data, many=True)
        return Response({"recommendations": serializer.data}, status=status.HTTP_200_OK)
        
    # 2. 일기 작성 완료 후 최초 추천 결과 저장 연산 (POST)
    elif request.method == 'POST':
        req_serializer = serializers.ContentRecommendationRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        
        mode = req_serializer.validated_data.get('mode', 'maintain')
        count = req_serializer.validated_data.get('count', 3)
        
        raw_emotion = getattr(diary_obj, 'emotion', None)
        user_6d_emotion = {
            'joy': getattr(raw_emotion, 'joy', 0.0),
            'sadness': getattr(raw_emotion, 'sadness', 0.0),
            'anger': getattr(raw_emotion, 'anger', 0.0),
            'fear': getattr(raw_emotion, 'fear', 0.0),
            'trust': getattr(raw_emotion, 'trust', 0.0),
            'surprise': getattr(raw_emotion, 'surprise', 0.0),
        }
        
        data = services.get_or_create_music_recommendation(diary_obj, user_6d_emotion, mode, count)
        res_serializer = serializers.MusicResponseSerializer(data, many=True)
        return Response({"mode": mode, "recommendations": res_serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_movie_view(request, diary_id):
    diary_obj = get_object_or_404(Diary, id=diary_id, user=request.user)
    
    # 1. 달력 클릭 시 과거 저장 데이터 복원 조회 (GET)
    if request.method == 'GET':
        data = services.get_saved_movie_metadata(diary_obj)
        serializer = serializers.MovieResponseSerializer(data, many=True)
        return Response({"recommendations": serializer.data}, status=status.HTTP_200_OK)
        
    # 2. 일기 작성 완료 후 최초 추천 결과 저장 연산 (POST)
    elif request.method == 'POST':
        req_serializer = serializers.ContentRecommendationRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        
        mode = req_serializer.validated_data.get('mode', 'maintain')
        count = req_serializer.validated_data.get('count', 3)
        
        raw_emotion = getattr(diary_obj, 'emotion', None)
        user_6d_emotion = {
            'joy': getattr(raw_emotion, 'joy', 0.0),
            'sadness': getattr(raw_emotion, 'sadness', 0.0),
            'anger': getattr(raw_emotion, 'anger', 0.0),
            'fear': getattr(raw_emotion, 'fear', 0.0),
            'trust': getattr(raw_emotion, 'trust', 0.0),
            'surprise': getattr(raw_emotion, 'surprise', 0.0),
        }
        
        data = services.get_or_create_movie_recommendation(diary_obj, user_6d_emotion, mode, count)
        res_serializer = serializers.MovieResponseSerializer(data, many=True)
        return Response({"mode": mode, "recommendations": res_serializer.data}, status=status.HTTP_200_OK)