from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from diary.models import Diary
from . import serializers
from . import services

@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_music_view(request, diary_id):
    diary_obj = get_object_or_404(Diary, id=diary_id, user=request.user)
    
    # 1. 달력 클릭 시 과거 데이터 복원 조회 (GET)
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
        
        # diary 앱의 emotion 분석 데이터 수집
        raw_emotion = getattr(diary_obj, 'emotion', {})
        if not raw_emotion:
            # 일기 데이터의 하위 상세 감정 매핑이 비어있을 시 딕셔너리 예외 대체
            raw_emotion = {}
            
        user_6d_emotion = services.convert_emotion_to_6d_vector(raw_emotion)
        
        data = services.get_or_create_music_recommendation(diary_obj, user_6d_emotion, mode, count)
        res_serializer = serializers.MusicResponseSerializer(data, many=True)
        return Response({"mode": mode, "recommendations": res_serializer.data}, status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def recommend_movie_view(request, diary_id):
    diary_obj = get_object_or_404(Diary, id=diary_id, user=request.user)
    
    # 1. 달력 클릭 시 과거 데이터 복원 조회 (GET)
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
        
        raw_emotion = getattr(diary_obj, 'emotion', {})
        if not raw_emotion:
            raw_emotion = {}
            
        user_6d_emotion = services.convert_emotion_to_6d_vector(raw_emotion)
        
        data = services.get_or_create_movie_recommendation(diary_obj, user_6d_emotion, mode, count)
        res_serializer = serializers.MovieResponseSerializer(data, many=True)
        return Response({"mode": mode, "recommendations": res_serializer.data}, status=status.HTTP_200_OK)