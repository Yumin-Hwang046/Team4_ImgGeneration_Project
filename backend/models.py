from sqlalchemy import Column, Integer, String, Text, DateTime, Date, ForeignKey, func
from sqlalchemy.orm import relationship

from backend.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)  # #회원ID #PK #사용자고유값
    email = Column(String(255), unique=True, nullable=False, index=True)  # #로그인이메일 #계정아이디 #중복불가
    password_hash = Column(String(255), nullable=False)  # #비밀번호해시값 #암호화비밀번호 #원문저장아님
    name = Column(String(100), nullable=False)  # #회원이름 #사용자표시이름
    role = Column(String(50), nullable=False, default="user")  # #권한구분 #기본user #관리자구분용
    is_active = Column(Integer, nullable=False, default=True)  # #계정활성여부 #1활성 #0비활성
    created_at = Column(DateTime, server_default=func.now())  # #회원생성일시 #가입시각
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #회원수정일시 #마지막변경시각

    generations = relationship("Generation", back_populates="user")
    upload_schedules = relationship("UploadSchedule", back_populates="user", cascade="all, delete-orphan")


class Generation(Base):
    __tablename__ = "generations"

    id = Column(Integer, primary_key=True, index=True)  # #생성건ID #PK #콘텐츠생성고유값
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # #회원ID #생성요청자ID #usersFK

    purpose = Column(String(50), nullable=True)  # #홍보목적 #방문유도 #브랜딩 #매출유도
    business_category = Column(String(100), nullable=True)  # #업종 #카페 #주점 #식당
    menu_name = Column(String(255), nullable=True)  # #메뉴명 #대표상품명 #홍보대상메뉴
    mood = Column(String(100), nullable=True)  # #원하는무드 #감성톤 #분위기
    location = Column(String(255), nullable=True)  # #지역 #매장위치 #타겟지역
    target_datetime = Column(DateTime, nullable=True)  # #목표일시 #홍보기준시간 #게시타이밍기준

    extra_info = Column(Text, nullable=True)  # #추가정보 #사용자추가요청 #에러메모 #분석메모
    generated_copy = Column(Text, nullable=True)  # #생성문구 #캡션 #홍보카피
    hashtags = Column(Text, nullable=True)  # #해시태그 #태그목록 #JSON문자열저장

    weather_summary = Column(String(255), nullable=True)  # #날씨요약 #기상정보 #추천근거데이터
    recommended_concept = Column(String(255), nullable=True)  # #추천콘셉트 #이미지방향 #홍보방향

    original_image_url = Column(String(500), nullable=True)  # #원본이미지URL #업로드원본경로
    generated_image_url = Column(String(500), nullable=True)  # #생성이미지URL #대표결과이미지
    image_mode = Column(String(50), nullable=True)  # #이미지모드 #generated #uploaded_and_analyzed
    generation_status = Column(String(50), nullable=False, default="SUCCESS")  # #생성상태 #PENDING #SUCCESS #FAILED

    created_at = Column(DateTime, server_default=func.now())  # #생성등록일시 #요청생성시각
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #생성수정일시 #상태변경시각

    user = relationship("User", back_populates="generations")
    generated_images = relationship(
        "GeneratedImage",
        back_populates="generation",
        cascade="all, delete-orphan",
    )
    upload_schedules = relationship(
        "UploadSchedule",
        back_populates="generation",
        cascade="all, delete-orphan",
    )


class GeneratedImage(Base):
    __tablename__ = "generated_images"

    id = Column(Integer, primary_key=True, index=True)  # #생성이미지ID #PK #이미지버전고유값
    generation_id = Column(Integer, ForeignKey("generations.id", ondelete="CASCADE"), nullable=False)  # #생성건ID #generationsFK #원본생성건연결

    image_url = Column(String(500), nullable=False)  # #이미지URL #생성된원본결과경로
    final_image_url = Column(String(500), nullable=True)  # #최종이미지URL #후처리완료본 #오버레이적용본
    prompt_used = Column(Text, nullable=True)  # #사용프롬프트 #생성근거문장
    version_no = Column(Integer, nullable=False, default=1)  # #버전번호 #재생성회차
    image_type = Column(String(50), nullable=False, default="generated")  # #이미지유형 #generated기본값
    status = Column(String(50), nullable=False, default="SUCCESS")  # #이미지상태 #SUCCESS #FAILED

    created_at = Column(DateTime, server_default=func.now())  # #이미지생성일시
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #이미지수정일시

    generation = relationship("Generation", back_populates="generated_images")


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(Integer, primary_key=True, index=True)  # #행사ID #PK #캘린더이벤트고유값
    event_date = Column(Date, nullable=False, index=True)  # #행사날짜 #이벤트일자
    title = Column(String(255), nullable=False)  # #행사명 #이벤트제목
    event_type = Column(String(50), nullable=False)  # #행사유형 #holiday #festival #local_event
    location = Column(String(255), nullable=True)  # #행사지역 #행사위치
    description = Column(Text, nullable=True)  # #행사설명 #상세내용 #메모

    created_at = Column(DateTime, server_default=func.now())  # #행사등록일시
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #행사수정일시


class UploadSchedule(Base):
    __tablename__ = "upload_schedules"

    id = Column(Integer, primary_key=True, index=True)  # #예약ID #PK #업로드예약고유값
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # #회원ID #예약사용자ID #usersFK
    generation_id = Column(Integer, ForeignKey("generations.id", ondelete="CASCADE"), nullable=False)  # #생성건ID #예약대상콘텐츠ID #generationsFK

    scheduled_at = Column(DateTime, nullable=False, index=True)  # #예약업로드일시 #게시예정시각
    channel = Column(String(50), nullable=False)  # #업로드채널 #instagram_feed #instagram_story
    status = Column(String(50), nullable=False, default="PENDING")  # #예약상태 #PENDING #SUCCESS #FAILED #CANCELED

    created_at = Column(DateTime, server_default=func.now())  # #예약생성일시
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # #예약수정일시

    user = relationship("User", back_populates="upload_schedules")
    generation = relationship("Generation", back_populates="upload_schedules")